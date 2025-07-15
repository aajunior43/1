# -*- coding: utf-8 -*-
"""
Módulo Core do Organizador de Arquivos com IA
Contém a lógica principal de organização e filtros
"""

__version__ = "2.0.0"
__author__ = "Organizador IA Team"
__description__ = "Lógica principal de organização de arquivos"

from .organizer import AdvancedOrganizer, organizer
from .filters import (
    FileFilter, SizeFilter, DateFilter, ExtensionFilter,
    NameFilter, CategoryFilter, HiddenFileFilter, ReadOnlyFilter,
    FilterManager, SmartFilter, filter_manager
)

__all__ = [
    "AdvancedOrganizer", "organizer",
    "FileFilter", "SizeFilter", "DateFilter", "ExtensionFilter",
    "NameFilter", "CategoryFilter", "HiddenFileFilter", "ReadOnlyFilter",
    "FilterManager", "SmartFilter", "filter_manager"
]