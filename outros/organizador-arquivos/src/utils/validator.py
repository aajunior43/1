# -*- coding: utf-8 -*-
"""
Sistema de validação para o Organizador de Arquivos
"""

import os
import stat
import psutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import mimetypes

from .logger import logger

class FileValidator:
    """Validador de arquivos e operações"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def clear_messages(self):
        """Limpa mensagens de erro e aviso"""
        self.errors.clear()
        self.warnings.clear()
    
    def validate_folder_access(self, folder_path: str) -> bool:
        """Valida se a pasta pode ser acessada e modificada"""
        try:
            path = Path(folder_path)
            
            # Verificar se existe
            if not path.exists():
                self.errors.append(f"Pasta não encontrada: {folder_path}")
                return False
            
            # Verificar se é diretório
            if not path.is_dir():
                self.errors.append(f"Caminho não é uma pasta: {folder_path}")
                return False
            
            # Verificar permissões de leitura
            if not os.access(path, os.R_OK):
                self.errors.append(f"Sem permissão de leitura: {folder_path}")
                return False
            
            # Verificar permissões de escrita
            if not os.access(path, os.W_OK):
                self.errors.append(f"Sem permissão de escrita: {folder_path}")
                return False
            
            # Verificar se não é pasta do sistema (Windows)
            system_folders = [
                "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
                "C:\\System Volume Information", "C:\\$Recycle.Bin"
            ]
            
            for sys_folder in system_folders:
                if str(path).lower().startswith(sys_folder.lower()):
                    self.errors.append(f"Pasta do sistema não pode ser organizada: {folder_path}")
                    return False
            
            return True
            
        except Exception as e:
            self.errors.append(f"Erro ao validar pasta: {str(e)}")
            return False
    
    def validate_disk_space(self, folder_path: str, required_space_mb: float = 100) -> bool:
        """Valida se há espaço suficiente em disco"""
        try:
            # Obter informações do disco
            disk_usage = psutil.disk_usage(folder_path)
            free_space_mb = disk_usage.free / (1024 * 1024)
            
            if free_space_mb < required_space_mb:
                self.warnings.append(
                    f"Pouco espaço em disco: {free_space_mb:.1f}MB disponível, "
                    f"recomendado: {required_space_mb}MB"
                )
                return False
            
            return True
            
        except Exception as e:
            self.warnings.append(f"Erro ao verificar espaço em disco: {str(e)}")
            return False
    
    def validate_file_access(self, file_path: str) -> bool:
        """Valida se um arquivo pode ser movido"""
        try:
            path = Path(file_path)
            
            # Verificar se existe
            if not path.exists():
                self.errors.append(f"Arquivo não encontrado: {file_path}")
                return False
            
            # Verificar se é arquivo
            if not path.is_file():
                self.warnings.append(f"Item não é um arquivo: {file_path}")
                return False
            
            # Verificar se não está em uso
            if self._is_file_in_use(path):
                self.warnings.append(f"Arquivo em uso: {path.name}")
                return False
            
            # Verificar permissões
            if not os.access(path, os.R_OK | os.W_OK):
                self.warnings.append(f"Sem permissão para mover: {path.name}")
                return False
            
            return True
            
        except Exception as e:
            self.errors.append(f"Erro ao validar arquivo {file_path}: {str(e)}")
            return False
    
    def _is_file_in_use(self, file_path: Path) -> bool:
        """Verifica se um arquivo está sendo usado por outro processo"""
        try:
            # Tentar abrir o arquivo em modo exclusivo
            with open(file_path, 'r+b') as f:
                pass
            return False
        except (IOError, OSError, PermissionError):
            return True
    
    def validate_file_size(self, file_path: str, max_size_mb: float = 1000) -> bool:
        """Valida o tamanho do arquivo"""
        try:
            path = Path(file_path)
            size_mb = path.stat().st_size / (1024 * 1024)
            
            if size_mb > max_size_mb:
                self.warnings.append(
                    f"Arquivo muito grande: {path.name} ({size_mb:.1f}MB)"
                )
                return False
            
            return True
            
        except Exception as e:
            self.warnings.append(f"Erro ao verificar tamanho do arquivo: {str(e)}")
            return False
    
    def validate_filename(self, filename: str) -> bool:
        """Valida se o nome do arquivo é válido"""
        # Caracteres inválidos no Windows
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        
        for char in invalid_chars:
            if char in filename:
                self.errors.append(f"Nome de arquivo inválido: {filename} (contém '{char}')")
                return False
        
        # Verificar nomes reservados do Windows
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            self.errors.append(f"Nome de arquivo reservado: {filename}")
            return False
        
        # Verificar comprimento
        if len(filename) > 255:
            self.errors.append(f"Nome de arquivo muito longo: {filename}")
            return False
        
        return True
    
    def get_file_info(self, file_path: str) -> Dict:
        """Obtém informações detalhadas do arquivo"""
        try:
            path = Path(file_path)
            stat_info = path.stat()
            
            # Detectar tipo MIME
            mime_type, _ = mimetypes.guess_type(str(path))
            
            return {
                "name": path.name,
                "size_bytes": stat_info.st_size,
                "size_mb": stat_info.st_size / (1024 * 1024),
                "extension": path.suffix.lower(),
                "mime_type": mime_type,
                "created": stat_info.st_ctime,
                "modified": stat_info.st_mtime,
                "accessed": stat_info.st_atime,
                "is_hidden": bool(stat_info.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN) if hasattr(stat, 'FILE_ATTRIBUTE_HIDDEN') else path.name.startswith('.'),
                "is_readonly": not bool(stat_info.st_mode & stat.S_IWRITE),
                "permissions": oct(stat_info.st_mode)[-3:]
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter informações do arquivo {file_path}", e)
            return {}
    
    def scan_folder_issues(self, folder_path: str) -> Dict:
        """Escaneia pasta em busca de possíveis problemas"""
        issues = {
            "inaccessible_files": [],
            "large_files": [],
            "files_in_use": [],
            "invalid_names": [],
            "hidden_files": [],
            "readonly_files": []
        }
        
        try:
            path = Path(folder_path)
            
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    file_info = self.get_file_info(str(file_path))
                    
                    # Verificar acessibilidade
                    if not self.validate_file_access(str(file_path)):
                        issues["inaccessible_files"].append(str(file_path))
                    
                    # Verificar tamanho
                    if file_info.get("size_mb", 0) > 500:  # Arquivos > 500MB
                        issues["large_files"].append({
                            "path": str(file_path),
                            "size_mb": file_info["size_mb"]
                        })
                    
                    # Verificar se está em uso
                    if self._is_file_in_use(file_path):
                        issues["files_in_use"].append(str(file_path))
                    
                    # Verificar nome
                    if not self.validate_filename(file_path.name):
                        issues["invalid_names"].append(str(file_path))
                    
                    # Verificar se é oculto
                    if file_info.get("is_hidden", False):
                        issues["hidden_files"].append(str(file_path))
                    
                    # Verificar se é somente leitura
                    if file_info.get("is_readonly", False):
                        issues["readonly_files"].append(str(file_path))
            
        except Exception as e:
            logger.error(f"Erro ao escanear pasta {folder_path}", e)
        
        return issues
    
    def get_validation_summary(self) -> Dict:
        """Retorna resumo das validações"""
        return {
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
            "has_errors": len(self.errors) > 0,
            "has_warnings": len(self.warnings) > 0,
            "total_issues": len(self.errors) + len(self.warnings)
        }

class OperationValidator:
    """Validador de operações de organização"""
    
    def __init__(self):
        self.file_validator = FileValidator()
    
    def validate_organization_operation(self, source_folder: str, files_to_move: List[Dict]) -> Tuple[bool, Dict]:
        """Valida uma operação completa de organização"""
        self.file_validator.clear_messages()
        
        # Validar pasta origem
        if not self.file_validator.validate_folder_access(source_folder):
            return False, self.file_validator.get_validation_summary()
        
        # Validar espaço em disco
        total_size_mb = sum(
            Path(file_info["source"]).stat().st_size / (1024 * 1024)
            for file_info in files_to_move
            if Path(file_info["source"]).exists()
        )
        
        self.file_validator.validate_disk_space(source_folder, total_size_mb + 100)
        
        # Validar cada arquivo
        valid_files = []
        for file_info in files_to_move:
            source_path = file_info["source"]
            
            if self.file_validator.validate_file_access(source_path):
                valid_files.append(file_info)
        
        # Verificar conflitos de destino
        destination_conflicts = self._check_destination_conflicts(files_to_move)
        
        summary = self.file_validator.get_validation_summary()
        summary["valid_files"] = valid_files
        summary["total_files"] = len(files_to_move)
        summary["destination_conflicts"] = destination_conflicts
        
        # Operação é válida se não há erros críticos
        is_valid = not summary["has_errors"]
        
        return is_valid, summary
    
    def _check_destination_conflicts(self, files_to_move: List[Dict]) -> List[Dict]:
        """Verifica conflitos de destino"""
        conflicts = []
        destinations = {}
        
        for file_info in files_to_move:
            dest_path = file_info["destination"]
            
            if dest_path in destinations:
                conflicts.append({
                    "destination": dest_path,
                    "files": [destinations[dest_path], file_info["source"]]
                })
            else:
                destinations[dest_path] = file_info["source"]
        
        return conflicts

# Instâncias globais
file_validator = FileValidator()
operation_validator = OperationValidator()