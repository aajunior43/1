# -*- coding: utf-8 -*-
"""
Sistema de backup automático para o Organizador de Arquivos
"""

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import threading
import time

from .logger import logger

class BackupManager:
    """Gerenciador de backups automáticos"""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or Path(__file__).parent.parent.parent / "config" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivo de índice de backups
        self.index_file = self.backup_dir / "backup_index.json"
        self.backups_index = self._load_index()
    
    def _load_index(self) -> Dict:
        """Carrega índice de backups"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Erro ao carregar índice de backups", e)
        return {"backups": [], "last_cleanup": None}
    
    def _save_index(self):
        """Salva índice de backups"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.backups_index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Erro ao salvar índice de backups", e)
    
    def create_backup(self, operation_data: Dict) -> Optional[str]:
        """Cria backup antes de uma operação"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_name
            
            # Dados do backup
            backup_data = {
                "timestamp": timestamp,
                "datetime": datetime.now().isoformat(),
                "operation_type": operation_data.get("type", "unknown"),
                "source_folder": operation_data.get("source_folder"),
                "files_moved": operation_data.get("files_moved", []),
                "organization_mode": operation_data.get("mode"),
                "total_files": len(operation_data.get("files_moved", [])),
                "backup_version": "2.0"
            }
            
            # Salvar backup
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            # Atualizar índice
            self.backups_index["backups"].append({
                "id": timestamp,
                "file": backup_name,
                "datetime": backup_data["datetime"],
                "operation_type": backup_data["operation_type"],
                "total_files": backup_data["total_files"],
                "source_folder": backup_data["source_folder"]
            })
            
            self._save_index()
            
            logger.info(f"Backup criado: {backup_name}", {
                "backup_id": timestamp,
                "files_count": backup_data["total_files"]
            })
            
            return timestamp
            
        except Exception as e:
            logger.error("Erro ao criar backup", e)
            return None
    
    def restore_backup(self, backup_id: str) -> bool:
        """Restaura um backup específico"""
        try:
            backup_file = self.backup_dir / f"backup_{backup_id}.json"
            
            if not backup_file.exists():
                logger.error(f"Backup não encontrado: {backup_id}")
                return False
            
            # Carregar dados do backup
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            files_moved = backup_data.get("files_moved", [])
            
            logger.operation_start("Restauração de Backup", {
                "backup_id": backup_id,
                "files_count": len(files_moved)
            })
            
            # Restaurar arquivos
            restored_count = 0
            errors = []
            
            for file_info in files_moved:
                try:
                    current_path = Path(file_info["destination"])
                    original_path = Path(file_info["source"])
                    
                    if current_path.exists():
                        # Criar diretório original se necessário
                        original_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Mover arquivo de volta
                        shutil.move(str(current_path), str(original_path))
                        restored_count += 1
                        
                        logger.file_operation("RESTAURADO", str(current_path), str(original_path))
                    
                except Exception as e:
                    error_msg = f"Erro ao restaurar {file_info.get('source', 'arquivo')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Remover pastas vazias criadas durante a organização
            self._cleanup_empty_folders(backup_data.get("source_folder"))
            
            success = len(errors) == 0
            
            logger.operation_end("Restauração de Backup", success, {
                "backup_id": backup_id,
                "restored_files": restored_count,
                "errors": len(errors)
            })
            
            return success
            
        except Exception as e:
            logger.error("Erro ao restaurar backup", e, {"backup_id": backup_id})
            return False
    
    def _cleanup_empty_folders(self, base_folder: str):
        """Remove pastas vazias após restauração"""
        try:
            base_path = Path(base_folder)
            
            # Procurar por pastas vazias
            for folder in base_path.iterdir():
                if folder.is_dir():
                    try:
                        # Tentar remover se estiver vazia
                        folder.rmdir()
                        logger.info(f"Pasta vazia removida: {folder.name}")
                    except OSError:
                        # Pasta não está vazia, ignorar
                        pass
        except Exception as e:
            logger.error("Erro ao limpar pastas vazias", e)
    
    def list_backups(self) -> List[Dict]:
        """Lista todos os backups disponíveis"""
        return sorted(
            self.backups_index.get("backups", []),
            key=lambda x: x.get("datetime", ""),
            reverse=True
        )
    
    def delete_backup(self, backup_id: str) -> bool:
        """Remove um backup específico"""
        try:
            backup_file = self.backup_dir / f"backup_{backup_id}.json"
            
            if backup_file.exists():
                backup_file.unlink()
                
                # Remover do índice
                self.backups_index["backups"] = [
                    b for b in self.backups_index["backups"]
                    if b.get("id") != backup_id
                ]
                
                self._save_index()
                
                logger.info(f"Backup removido: {backup_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error("Erro ao remover backup", e, {"backup_id": backup_id})
            return False
    
    def cleanup_old_backups(self, max_backups: int = 10):
        """Remove backups antigos mantendo apenas os mais recentes"""
        try:
            backups = self.list_backups()
            
            if len(backups) > max_backups:
                backups_to_remove = backups[max_backups:]
                
                for backup in backups_to_remove:
                    self.delete_backup(backup["id"])
                
                logger.info(f"Limpeza de backups concluída. Removidos: {len(backups_to_remove)}")
            
            # Atualizar timestamp da última limpeza
            self.backups_index["last_cleanup"] = datetime.now().isoformat()
            self._save_index()
            
        except Exception as e:
            logger.error("Erro na limpeza de backups", e)
    
    def get_backup_info(self, backup_id: str) -> Optional[Dict]:
        """Obtém informações detalhadas de um backup"""
        try:
            backup_file = self.backup_dir / f"backup_{backup_id}.json"
            
            if backup_file.exists():
                with open(backup_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error("Erro ao obter informações do backup", e, {"backup_id": backup_id})
            return None
    
    def auto_cleanup_thread(self, max_backups: int = 10, interval_hours: int = 24):
        """Thread para limpeza automática de backups"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(interval_hours * 3600)  # Converter horas para segundos
                    self.cleanup_old_backups(max_backups)
                except Exception as e:
                    logger.error("Erro na limpeza automática de backups", e)
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
        logger.info(f"Thread de limpeza automática iniciada (intervalo: {interval_hours}h)")

# Instância global do gerenciador de backup
backup_manager = BackupManager()