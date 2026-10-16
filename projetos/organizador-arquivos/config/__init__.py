# -*- coding: utf-8 -*-
"""
Módulo de Configurações do Organizador de Arquivos com IA
Gerencia configurações centralizadas da aplicação
"""

__version__ = "2.0.0"
__author__ = "Organizador IA Team"
__description__ = "Sistema de configurações centralizadas"

from .settings import Config, config, FILE_CATEGORIES, THEMES

__all__ = ["Config", "config", "FILE_CATEGORIES", "THEMES"]