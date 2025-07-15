# -*- coding: utf-8 -*-
"""
Organizador principal melhorado com funcionalidades avançadas
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
import threading
import time

from ..utils.logger import logger
from ..utils.backup import backup_manager
from ..utils.validator import file_validator, operation_validator
from .filters import filter_manager
from ..config.settings import config, FILE_CATEGORIES

class AdvancedOrganizer:
    """Organizador avançado de arquivos com funcionalidades melhoradas"""
    
    def __init__(self):
        self.is_running = False
        self.current_operation = None
        self.progress_callback: Optional[Callable] = None
        self.log_callback: Optional[Callable] = None
        self.cancel_requested = False
        
        # Estatísticas da operação atual
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "moved_files": 0,
            "skipped_files": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """Define callback para atualização de progresso"""
        self.progress_callback = callback
    
    def set_log_callback(self, callback: Callable[[str], None]):
        """Define callback para logs"""
        self.log_callback = callback
    
    def _log(self, message: str, level: str = "info"):
        """Log interno com callback"""
        if level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        
        if self.log_callback:
            self.log_callback(message)
    
    def _update_progress(self, current: int, total: int, message: str = ""):
        """Atualiza progresso com callback"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def analyze_folder(self, folder_path: str, organization_mode: str = "por_tipo") -> Dict:
        """Analisa pasta e retorna sugestões de organização"""
        try:
            self._log(f"🔍 Iniciando análise da pasta: {folder_path}")
            
            # Validar pasta
            if not file_validator.validate_folder_access(folder_path):
                validation_summary = file_validator.get_validation_summary()
                self._log(f"❌ Erro na validação da pasta: {validation_summary['errors']}", "error")
                return {"success": False, "errors": validation_summary["errors"]}
            
            # Obter lista de arquivos
            folder = Path(folder_path)
            all_files = list(folder.glob('*'))
            files = [f for f in all_files if f.is_file()]
            
            if not files:
                self._log("⚠️ Nenhum arquivo encontrado na pasta", "warning")
                return {"success": True, "suggestions": [], "stats": {}}
            
            self._log(f"📊 Encontrados {len(files)} arquivos para análise")
            
            # Obter informações detalhadas dos arquivos
            files_info = []
            for i, file_path in enumerate(files, 1):
                self._update_progress(i, len(files), f"Analisando: {file_path.name}")
                
                file_info = file_validator.get_file_info(str(file_path))
                file_info["path"] = str(file_path)
                file_info["category"] = self._get_file_category(file_path.suffix)
                
                files_info.append(file_info)
            
            # Aplicar filtros se configurados
            if filter_manager.filters:
                files_info = filter_manager.apply_filters(files_info)
                self._log(f"🔍 Filtros aplicados: {len(files_info)} arquivos selecionados")
            
            # Gerar sugestões de organização
            suggestions = self._generate_suggestions(files_info, folder_path, organization_mode)
            
            # Estatísticas
            stats = self._calculate_stats(files_info, suggestions)
            
            self._log(f"✅ Análise concluída: {len(suggestions)} sugestões geradas")
            
            return {
                "success": True,
                "suggestions": suggestions,
                "stats": stats,
                "files_info": files_info
            }
            
        except Exception as e:
            self._log(f"❌ Erro na análise: {str(e)}", "error")
            logger.error("Erro na análise da pasta", e)
            return {"success": False, "error": str(e)}
    
    def _get_file_category(self, extension: str) -> str:
        """Determina categoria do arquivo baseada na extensão"""
        extension = extension.lower()
        
        for category, info in FILE_CATEGORIES.items():
            if extension in info["extensions"]:
                return category
        
        return "Outros"
    
    def _generate_suggestions(self, files_info: List[Dict], base_folder: str, mode: str) -> List[Dict]:
        """Gera sugestões de organização"""
        suggestions = []
        base_path = Path(base_folder)
        
        for file_info in files_info:
            source_path = Path(file_info["path"])
            
            # Determinar pasta destino baseada no modo
            if mode == "por_tipo":
                category = file_info["category"]
                dest_folder = base_path / category
            elif mode == "por_data":
                modified_date = datetime.fromtimestamp(file_info["modified"])
                date_folder = f"{modified_date.year}-{modified_date.month:02d}"
                dest_folder = base_path / date_folder
            elif mode == "por_nome":
                first_char = file_info["name"][0].upper() if file_info["name"] else "#"
                if not first_char.isalpha():
                    first_char = "#"
                dest_folder = base_path / first_char
            else:
                dest_folder = base_path / "Organizados"
            
            # Determinar nome final (resolver conflitos)
            final_name = self._resolve_name_conflict(dest_folder, file_info["name"])
            final_path = dest_folder / final_name
            
            suggestion = {
                "source": str(source_path),
                "destination": str(final_path),
                "source_name": file_info["name"],
                "final_name": final_name,
                "category": file_info.get("category", "Outros"),
                "dest_folder": str(dest_folder),
                "dest_folder_name": dest_folder.name,
                "size_mb": file_info["size_mb"],
                "file_info": file_info
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _resolve_name_conflict(self, dest_folder: Path, filename: str) -> str:
        """Resolve conflitos de nome de arquivo"""
        if not dest_folder.exists():
            return filename
        
        dest_path = dest_folder / filename
        if not dest_path.exists():
            return filename
        
        # Arquivo já existe, adicionar sufixo numérico
        name_stem = Path(filename).stem
        extension = Path(filename).suffix
        counter = 1
        
        while True:
            new_name = f"{name_stem}_{counter}{extension}"
            new_path = dest_folder / new_name
            
            if not new_path.exists():
                return new_name
            
            counter += 1
            
            # Evitar loop infinito
            if counter > 9999:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                return f"{name_stem}_{timestamp}{extension}"
    
    def _calculate_stats(self, files_info: List[Dict], suggestions: List[Dict]) -> Dict:
        """Calcula estatísticas da análise"""
        total_size_mb = sum(f["size_mb"] for f in files_info)
        
        # Estatísticas por categoria
        categories_stats = {}
        for suggestion in suggestions:
            category = suggestion["category"]
            if category not in categories_stats:
                categories_stats[category] = {"count": 0, "size_mb": 0}
            
            categories_stats[category]["count"] += 1
            categories_stats[category]["size_mb"] += suggestion["size_mb"]
        
        return {
            "total_files": len(files_info),
            "total_size_mb": total_size_mb,
            "categories_count": len(categories_stats),
            "categories_stats": categories_stats,
            "largest_file": max(files_info, key=lambda x: x["size_mb"]) if files_info else None,
            "smallest_file": min(files_info, key=lambda x: x["size_mb"]) if files_info else None
        }
    
    def execute_organization(self, suggestions: List[Dict], create_backup: bool = True) -> Dict:
        """Executa a organização dos arquivos"""
        if self.is_running:
            return {"success": False, "error": "Operação já em andamento"}
        
        self.is_running = True
        self.cancel_requested = False
        self.stats = {
            "total_files": len(suggestions),
            "processed_files": 0,
            "moved_files": 0,
            "skipped_files": 0,
            "errors": 0,
            "start_time": datetime.now(),
            "end_time": None
        }
        
        try:
            self._log(f"🚀 Iniciando organização de {len(suggestions)} arquivos")
            
            # Validar operação
            is_valid, validation_summary = operation_validator.validate_organization_operation(
                Path(suggestions[0]["source"]).parent if suggestions else "",
                [{"source": s["source"], "destination": s["destination"]} for s in suggestions]
            )
            
            if not is_valid:
                self._log(f"❌ Validação falhou: {validation_summary['errors']}", "error")
                return {"success": False, "errors": validation_summary["errors"]}
            
            # Criar backup se solicitado
            backup_id = None
            if create_backup and config.get("auto_backup", True):
                backup_data = {
                    "type": "organization",
                    "source_folder": str(Path(suggestions[0]["source"]).parent),
                    "files_moved": [{"source": s["source"], "destination": s["destination"]} for s in suggestions],
                    "mode": "advanced_organization"
                }
                backup_id = backup_manager.create_backup(backup_data)
                if backup_id:
                    self._log(f"💾 Backup criado: {backup_id}")
            
            # Executar movimentação dos arquivos
            moved_files = []
            errors = []
            
            for i, suggestion in enumerate(suggestions, 1):
                if self.cancel_requested:
                    self._log("⏹️ Operação cancelada pelo usuário", "warning")
                    break
                
                self._update_progress(i, len(suggestions), f"Movendo: {suggestion['source_name']}")
                
                try:
                    source_path = Path(suggestion["source"])
                    dest_path = Path(suggestion["destination"])
                    
                    # Criar pasta destino se não existir
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Mover arquivo
                    shutil.move(str(source_path), str(dest_path))
                    
                    moved_files.append(suggestion)
                    self.stats["moved_files"] += 1
                    
                    self._log(f"✅ Movido: {suggestion['source_name']} -> {suggestion['dest_folder_name']}/")
                    
                except Exception as e:
                    error_msg = f"Erro ao mover {suggestion['source_name']}: {str(e)}"
                    errors.append(error_msg)
                    self.stats["errors"] += 1
                    self._log(f"❌ {error_msg}", "error")
                
                self.stats["processed_files"] += 1
            
            self.stats["end_time"] = datetime.now()
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            
            # Log final
            self._log("\n" + "=" * 60)
            self._log("📊 RESULTADO DA ORGANIZAÇÃO:")
            self._log(f"   ✅ Arquivos movidos: {self.stats['moved_files']}")
            self._log(f"   ❌ Erros: {self.stats['errors']}")
            self._log(f"   ⏱️ Tempo total: {duration:.1f}s")
            self._log("=" * 60)
            
            success = self.stats["errors"] == 0 and not self.cancel_requested
            
            return {
                "success": success,
                "stats": self.stats.copy(),
                "moved_files": moved_files,
                "errors": errors,
                "backup_id": backup_id,
                "duration_seconds": duration
            }
            
        except Exception as e:
            self._log(f"❌ Erro crítico na organização: {str(e)}", "error")
            logger.error("Erro crítico na organização", e)
            return {"success": False, "error": str(e)}
        
        finally:
            self.is_running = False
    
    def cancel_operation(self):
        """Cancela a operação em andamento"""
        if self.is_running:
            self.cancel_requested = True
            self._log("⏹️ Cancelamento solicitado...", "warning")
    
    def get_operation_stats(self) -> Dict:
        """Retorna estatísticas da operação atual"""
        return self.stats.copy()
    
    def create_custom_organization_rule(self, name: str, rule_function: Callable[[Dict], str]) -> bool:
        """Cria regra customizada de organização"""
        try:
            # Salvar regra customizada (implementação simplificada)
            custom_rules = config.get("custom_rules", {})
            custom_rules[name] = {
                "name": name,
                "created": datetime.now().isoformat(),
                "description": f"Regra customizada: {name}"
            }
            config.set("custom_rules", custom_rules)
            
            self._log(f"📝 Regra customizada criada: {name}")
            return True
            
        except Exception as e:
            self._log(f"❌ Erro ao criar regra customizada: {str(e)}", "error")
            return False
    
    def preview_organization(self, folder_path: str, mode: str) -> Dict:
        """Gera preview da organização sem executar"""
        analysis = self.analyze_folder(folder_path, mode)
        
        if not analysis["success"]:
            return analysis
        
        # Criar estrutura de preview
        preview_structure = {}
        
        for suggestion in analysis["suggestions"]:
            folder_name = suggestion["dest_folder_name"]
            if folder_name not in preview_structure:
                preview_structure[folder_name] = []
            
            preview_structure[folder_name].append({
                "name": suggestion["final_name"],
                "size_mb": suggestion["size_mb"],
                "category": suggestion["category"]
            })
        
        return {
            "success": True,
            "preview_structure": preview_structure,
            "stats": analysis["stats"]
        }

# Instância global do organizador
organizer = AdvancedOrganizer()