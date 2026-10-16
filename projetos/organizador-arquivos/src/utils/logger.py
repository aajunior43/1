# -*- coding: utf-8 -*-
"""
Sistema de logging avançado para o Organizador de Arquivos
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

class OrganizadorLogger:
    """Logger personalizado para o organizador de arquivos"""
    
    def __init__(self, name: str = "OrganizadorArquivos"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Diretório de logs
        self.log_dir = Path(__file__).parent.parent.parent / "config" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivo de log atual
        self.log_file = self.log_dir / f"organizador_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Configurar handlers se ainda não existirem
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Configura os handlers de logging"""
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para arquivo
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Adicionar handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str, extra_data: Optional[dict] = None):
        """Log de informação"""
        if extra_data:
            message = f"{message} | Data: {json.dumps(extra_data, ensure_ascii=False)}"
        self.logger.info(message)
    
    def warning(self, message: str, extra_data: Optional[dict] = None):
        """Log de aviso"""
        if extra_data:
            message = f"{message} | Data: {json.dumps(extra_data, ensure_ascii=False)}"
        self.logger.warning(message)
    
    def error(self, message: str, exception: Optional[Exception] = None, extra_data: Optional[dict] = None):
        """Log de erro"""
        if extra_data:
            message = f"{message} | Data: {json.dumps(extra_data, ensure_ascii=False)}"
        if exception:
            self.logger.error(f"{message} | Exception: {str(exception)}", exc_info=True)
        else:
            self.logger.error(message)
    
    def debug(self, message: str, extra_data: Optional[dict] = None):
        """Log de debug"""
        if extra_data:
            message = f"{message} | Data: {json.dumps(extra_data, ensure_ascii=False)}"
        self.logger.debug(message)
    
    def operation_start(self, operation: str, details: dict):
        """Log de início de operação"""
        self.info(f"🚀 INÍCIO: {operation}", details)
    
    def operation_end(self, operation: str, success: bool, details: dict):
        """Log de fim de operação"""
        status = "✅ SUCESSO" if success else "❌ FALHA"
        self.info(f"{status}: {operation}", details)
    
    def file_operation(self, action: str, source: str, destination: str = None):
        """Log de operação de arquivo"""
        details = {"action": action, "source": source}
        if destination:
            details["destination"] = destination
        self.info(f"📁 {action}: {Path(source).name}", details)
    
    def get_log_content(self, lines: int = 100) -> str:
        """Obtém conteúdo do log atual"""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    return ''.join(all_lines[-lines:] if len(all_lines) > lines else all_lines)
            return "Nenhum log disponível"
        except Exception as e:
            return f"Erro ao ler log: {str(e)}"
    
    def export_log(self, export_path: str) -> bool:
        """Exporta log atual para arquivo específico"""
        try:
            if self.log_file.exists():
                import shutil
                shutil.copy2(self.log_file, export_path)
                return True
            return False
        except Exception as e:
            self.error("Erro ao exportar log", e)
            return False
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Remove logs antigos"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            for log_file in self.log_dir.glob("organizador_*.log"):
                if log_file.stat().st_mtime < cutoff_date:
                    log_file.unlink()
                    self.info(f"Log antigo removido: {log_file.name}")
        except Exception as e:
            self.error("Erro ao limpar logs antigos", e)

# Instância global do logger
logger = OrganizadorLogger()

# Funções de conveniência
def log_info(message: str, extra_data: Optional[dict] = None):
    logger.info(message, extra_data)

def log_warning(message: str, extra_data: Optional[dict] = None):
    logger.warning(message, extra_data)

def log_error(message: str, exception: Optional[Exception] = None, extra_data: Optional[dict] = None):
    logger.error(message, exception, extra_data)

def log_debug(message: str, extra_data: Optional[dict] = None):
    logger.debug(message, extra_data)