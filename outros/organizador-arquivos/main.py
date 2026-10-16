#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Organizador de Arquivos com IA - Versão Avançada
Ponto de entrada principal da aplicação
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório src ao path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from src.gui.main_window import main
    from src.utils.logger import logger
    from src.config.settings import config
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Certifique-se de que todos os arquivos estão no local correto.")
    sys.exit(1)

def check_dependencies():
    """Verifica se todas as dependências estão instaladas"""
    required_modules = [
        'tkinter',
        'pathlib',
        'json',
        'datetime',
        'threading',
        'shutil'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ Módulos não encontrados: {', '.join(missing_modules)}")
        print("Por favor, instale as dependências necessárias.")
        return False
    
    return True

def setup_environment():
    """Configura o ambiente da aplicação"""
    try:
        # Criar diretórios necessários
        directories = [
            "logs",
            "backups",
            "config",
            "temp"
        ]
        
        for directory in directories:
            dir_path = Path(directory)
            dir_path.mkdir(exist_ok=True)
        
        # Inicializar logger
        logger.info("🚀 Iniciando Organizador de Arquivos com IA")
        logger.info(f"📁 Diretório de trabalho: {Path.cwd()}")
        
        # Carregar configurações
        config.load()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao configurar ambiente: {e}")
        return False

def show_startup_info():
    """Mostra informações de inicialização"""
    print("\n" + "=" * 60)
    print("🗂️  ORGANIZADOR DE ARQUIVOS COM IA - VERSÃO AVANÇADA")
    print("=" * 60)
    print("📋 Funcionalidades:")
    print("   • Organização inteligente por tipo, data ou nome")
    print("   • Filtros avançados de arquivos")
    print("   • Sistema de backup automático")
    print("   • Interface gráfica moderna")
    print("   • Logs detalhados de operações")
    print("   • Preview de organização")
    print("   • Temas claro e escuro")
    print("\n🚀 Iniciando aplicação...")
    print("=" * 60 + "\n")

def main_entry():
    """Ponto de entrada principal"""
    try:
        # Mostrar informações de inicialização
        show_startup_info()
        
        # Verificar dependências
        if not check_dependencies():
            input("\nPressione Enter para sair...")
            return 1
        
        # Configurar ambiente
        if not setup_environment():
            input("\nPressione Enter para sair...")
            return 1
        
        # Executar aplicação
        logger.info("✅ Ambiente configurado com sucesso")
        logger.info("🎯 Iniciando interface gráfica")
        
        main()
        
        logger.info("👋 Aplicação finalizada")
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ Aplicação interrompida pelo usuário")
        logger.info("⏹️ Aplicação interrompida pelo usuário")
        return 0
        
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        logger.error("Erro crítico na aplicação", e)
        input("\nPressione Enter para sair...")
        return 1

if __name__ == "__main__":
    sys.exit(main_entry())