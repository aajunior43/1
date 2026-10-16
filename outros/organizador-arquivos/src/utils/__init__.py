# -*- coding: utf-8 -*-
"""
Módulo de Utilitários do Organizador de Arquivos com IA
Contém ferramentas auxiliares para logging, backup e validação
"""

__version__ = "2.0.0"
__author__ = "Organizador IA Team"
__description__ = "Utilitários para logging, backup e validação"

from .logger import OrganizadorLogger, logger
from .backup import BackupManager, backup_manager
from .validator import FileValidator, OperationValidator, file_validator, operation_validator

__all__ = [
    "OrganizadorLogger", "logger",
    "BackupManager", "backup_manager",
    "FileValidator", "OperationValidator", "file_validator", "operation_validator"
]