# -*- coding: utf-8 -*-
"""
Sistema de filtros avançados para o Organizador de Arquivos
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
import fnmatch

from ..utils.logger import logger

class FileFilter:
    """Classe base para filtros de arquivo"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def apply(self, file_info: Dict) -> bool:
        """Aplica o filtro ao arquivo. Retorna True se o arquivo passa no filtro"""
        raise NotImplementedError

class SizeFilter(FileFilter):
    """Filtro por tamanho de arquivo"""
    
    def __init__(self, min_size_mb: float = 0, max_size_mb: float = float('inf')):
        super().__init__(
            f"Tamanho ({min_size_mb}MB - {max_size_mb}MB)",
            f"Arquivos entre {min_size_mb}MB e {max_size_mb}MB"
        )
        self.min_size_mb = min_size_mb
        self.max_size_mb = max_size_mb
    
    def apply(self, file_info: Dict) -> bool:
        size_mb = file_info.get("size_mb", 0)
        return self.min_size_mb <= size_mb <= self.max_size_mb

class DateFilter(FileFilter):
    """Filtro por data de modificação"""
    
    def __init__(self, days_ago: int = None, start_date: datetime = None, end_date: datetime = None):
        if days_ago is not None:
            self.start_date = datetime.now() - timedelta(days=days_ago)
            self.end_date = datetime.now()
            name = f"Últimos {days_ago} dias"
        else:
            self.start_date = start_date
            self.end_date = end_date
            name = f"Data ({start_date.strftime('%d/%m/%Y') if start_date else 'início'} - {end_date.strftime('%d/%m/%Y') if end_date else 'fim'})"
        
        super().__init__(name, f"Arquivos modificados no período especificado")
    
    def apply(self, file_info: Dict) -> bool:
        modified_timestamp = file_info.get("modified", 0)
        modified_date = datetime.fromtimestamp(modified_timestamp)
        
        if self.start_date and modified_date < self.start_date:
            return False
        if self.end_date and modified_date > self.end_date:
            return False
        
        return True

class ExtensionFilter(FileFilter):
    """Filtro por extensão de arquivo"""
    
    def __init__(self, extensions: List[str], include: bool = True):
        self.extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]
        self.include = include
        
        action = "Incluir" if include else "Excluir"
        super().__init__(
            f"{action} extensões: {', '.join(self.extensions)}",
            f"{action} arquivos com as extensões especificadas"
        )
    
    def apply(self, file_info: Dict) -> bool:
        extension = file_info.get("extension", "").lower()
        has_extension = extension in self.extensions
        return has_extension if self.include else not has_extension

class NameFilter(FileFilter):
    """Filtro por nome de arquivo"""
    
    def __init__(self, pattern: str, use_regex: bool = False, case_sensitive: bool = False):
        self.pattern = pattern
        self.use_regex = use_regex
        self.case_sensitive = case_sensitive
        
        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            self.regex = re.compile(pattern, flags)
        
        super().__init__(
            f"Nome: {pattern} ({'regex' if use_regex else 'padrão'})",
            f"Filtrar por nome usando {'expressão regular' if use_regex else 'padrão de texto'}"
        )
    
    def apply(self, file_info: Dict) -> bool:
        filename = file_info.get("name", "")
        
        if not self.case_sensitive:
            filename = filename.lower()
            pattern = self.pattern.lower()
        else:
            pattern = self.pattern
        
        if self.use_regex:
            return bool(self.regex.search(filename))
        else:
            # Usar fnmatch para padrões com wildcards (* e ?)
            return fnmatch.fnmatch(filename, pattern)

class CategoryFilter(FileFilter):
    """Filtro por categoria de arquivo"""
    
    def __init__(self, categories: List[str], include: bool = True):
        self.categories = [cat.lower() for cat in categories]
        self.include = include
        
        action = "Incluir" if include else "Excluir"
        super().__init__(
            f"{action} categorias: {', '.join(categories)}",
            f"{action} arquivos das categorias especificadas"
        )
    
    def apply(self, file_info: Dict) -> bool:
        category = file_info.get("category", "").lower()
        has_category = category in self.categories
        return has_category if self.include else not has_category

class HiddenFileFilter(FileFilter):
    """Filtro para arquivos ocultos"""
    
    def __init__(self, include_hidden: bool = False):
        self.include_hidden = include_hidden
        
        super().__init__(
            f"{'Incluir' if include_hidden else 'Excluir'} arquivos ocultos",
            f"{'Incluir' if include_hidden else 'Excluir'} arquivos e pastas ocultos"
        )
    
    def apply(self, file_info: Dict) -> bool:
        is_hidden = file_info.get("is_hidden", False)
        return not is_hidden or self.include_hidden

class ReadOnlyFilter(FileFilter):
    """Filtro para arquivos somente leitura"""
    
    def __init__(self, include_readonly: bool = True):
        self.include_readonly = include_readonly
        
        super().__init__(
            f"{'Incluir' if include_readonly else 'Excluir'} arquivos somente leitura",
            f"{'Incluir' if include_readonly else 'Excluir'} arquivos marcados como somente leitura"
        )
    
    def apply(self, file_info: Dict) -> bool:
        is_readonly = file_info.get("is_readonly", False)
        return not is_readonly or self.include_readonly

class FilterManager:
    """Gerenciador de filtros"""
    
    def __init__(self):
        self.filters: List[FileFilter] = []
        self.presets = self._create_presets()
    
    def add_filter(self, filter_obj: FileFilter):
        """Adiciona um filtro"""
        self.filters.append(filter_obj)
        logger.debug(f"Filtro adicionado: {filter_obj.name}")
    
    def remove_filter(self, filter_name: str):
        """Remove um filtro pelo nome"""
        self.filters = [f for f in self.filters if f.name != filter_name]
        logger.debug(f"Filtro removido: {filter_name}")
    
    def clear_filters(self):
        """Remove todos os filtros"""
        self.filters.clear()
        logger.debug("Todos os filtros removidos")
    
    def apply_filters(self, files_info: List[Dict]) -> List[Dict]:
        """Aplica todos os filtros à lista de arquivos"""
        if not self.filters:
            return files_info
        
        filtered_files = []
        
        for file_info in files_info:
            # Arquivo passa se atende a todos os filtros
            passes_all_filters = all(filter_obj.apply(file_info) for filter_obj in self.filters)
            
            if passes_all_filters:
                filtered_files.append(file_info)
        
        logger.info(f"Filtros aplicados: {len(files_info)} -> {len(filtered_files)} arquivos")
        return filtered_files
    
    def get_filter_summary(self) -> Dict:
        """Retorna resumo dos filtros ativos"""
        return {
            "total_filters": len(self.filters),
            "filters": [{
                "name": f.name,
                "description": f.description
            } for f in self.filters]
        }
    
    def _create_presets(self) -> Dict[str, List[FileFilter]]:
        """Cria filtros predefinidos"""
        return {
            "apenas_imagens": [
                ExtensionFilter([".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg"])
            ],
            "apenas_documentos": [
                ExtensionFilter([".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"])
            ],
            "arquivos_grandes": [
                SizeFilter(min_size_mb=100)
            ],
            "arquivos_pequenos": [
                SizeFilter(max_size_mb=1)
            ],
            "ultimos_30_dias": [
                DateFilter(days_ago=30)
            ],
            "sem_arquivos_ocultos": [
                HiddenFileFilter(include_hidden=False)
            ],
            "apenas_videos": [
                ExtensionFilter([".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm", ".m4v"])
            ],
            "apenas_audio": [
                ExtensionFilter([".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma", ".m4a"])
            ]
        }
    
    def apply_preset(self, preset_name: str) -> bool:
        """Aplica um filtro predefinido"""
        if preset_name in self.presets:
            self.clear_filters()
            for filter_obj in self.presets[preset_name]:
                self.add_filter(filter_obj)
            logger.info(f"Preset aplicado: {preset_name}")
            return True
        return False
    
    def get_available_presets(self) -> List[str]:
        """Retorna lista de presets disponíveis"""
        return list(self.presets.keys())
    
    def create_custom_preset(self, name: str, filters: List[FileFilter]):
        """Cria um preset customizado"""
        self.presets[name] = filters
        logger.info(f"Preset customizado criado: {name}")
    
    def save_current_as_preset(self, name: str):
        """Salva filtros atuais como preset"""
        self.presets[name] = self.filters.copy()
        logger.info(f"Filtros atuais salvos como preset: {name}")

class SmartFilter:
    """Filtro inteligente que combina múltiplos critérios"""
    
    def __init__(self):
        self.filter_manager = FilterManager()
    
    def create_smart_filter_for_cleanup(self) -> FilterManager:
        """Cria filtro inteligente para limpeza de arquivos"""
        manager = FilterManager()
        
        # Arquivos temporários
        manager.add_filter(ExtensionFilter([".tmp", ".temp", ".cache", ".log"], include=True))
        
        # Arquivos antigos (mais de 90 dias)
        manager.add_filter(DateFilter(days_ago=90))
        
        # Excluir arquivos muito grandes (podem ser importantes)
        manager.add_filter(SizeFilter(max_size_mb=500))
        
        return manager
    
    def create_media_organizer_filter(self) -> FilterManager:
        """Cria filtro para organização de mídia"""
        manager = FilterManager()
        
        # Apenas arquivos de mídia
        media_extensions = [
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg",
            ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm", ".m4v",
            ".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma", ".m4a"
        ]
        manager.add_filter(ExtensionFilter(media_extensions, include=True))
        
        # Excluir arquivos muito pequenos (provavelmente thumbnails)
        manager.add_filter(SizeFilter(min_size_mb=0.1))
        
        return manager
    
    def create_document_organizer_filter(self) -> FilterManager:
        """Cria filtro para organização de documentos"""
        manager = FilterManager()
        
        # Apenas documentos
        doc_extensions = [
            ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt",
            ".xls", ".xlsx", ".ppt", ".pptx", ".csv"
        ]
        manager.add_filter(ExtensionFilter(doc_extensions, include=True))
        
        return manager

# Instância global do gerenciador de filtros
filter_manager = FilterManager()
smart_filter = SmartFilter()