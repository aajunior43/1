# -*- coding: utf-8 -*-
"""
Configuração principal do Organizador de Arquivos
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List

class Config:
    """Classe de configuração principal"""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent
        self.config_file = self.config_dir / "user_settings.json"
        self.backup_dir = self.config_dir / "backups"
        self.logs_dir = self.config_dir / "logs"
        
        # Criar diretórios se não existirem
        self.backup_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Configurações padrão
        self.default_settings = {
            "theme": "light",
            "default_organization_mode": "por_tipo",
            "auto_backup": True,
            "max_backups": 10,
            "show_hidden_files": False,
            "confirm_operations": True,
            "log_level": "INFO",
            "recent_folders": [],
            "custom_categories": {},
            "file_size_limit_mb": 1000,
            "language": "pt-BR",
            "auto_save_logs": True,
            "window_geometry": "1100x800",
            "enable_drag_drop": True,
            "show_file_preview": True
        }
        
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                # Mesclar com configurações padrão
                merged_settings = self.default_settings.copy()
                merged_settings.update(settings)
                return merged_settings
            except Exception as e:
                print(f"Erro ao carregar configurações: {e}")
                return self.default_settings.copy()
        return self.default_settings.copy()
    
    def save_settings(self) -> bool:
        """Salva configurações no arquivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")
            return False
    
    def get(self, key: str, default=None):
        """Obtém valor de configuração"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Define valor de configuração"""
        self.settings[key] = value
        self.save_settings()
    
    def add_recent_folder(self, folder_path: str):
        """Adiciona pasta aos recentes"""
        recent = self.settings.get("recent_folders", [])
        if folder_path in recent:
            recent.remove(folder_path)
        recent.insert(0, folder_path)
        # Manter apenas os 10 mais recentes
        self.settings["recent_folders"] = recent[:10]
        self.save_settings()
    
    def get_recent_folders(self) -> List[str]:
        """Obtém lista de pastas recentes"""
        return self.settings.get("recent_folders", [])

# Instância global de configuração
config = Config()

# Categorias de arquivo expandidas
FILE_CATEGORIES = {
    "Imagens": {
        "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".ico", ".raw", ".psd"],
        "icon": "🖼️",
        "color": "#10b981"
    },
    "Documentos": {
        "extensions": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
        "icon": "📄",
        "color": "#3b82f6"
    },
    "Videos": {
        "extensions": [".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm", ".m4v", ".3gp", ".mpg", ".mpeg"],
        "icon": "🎬",
        "color": "#ef4444"
    },
    "Audio": {
        "extensions": [".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma", ".m4a", ".opus", ".aiff"],
        "icon": "🎵",
        "color": "#8b5cf6"
    },
    "Compactados": {
        "extensions": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".cab", ".iso"],
        "icon": "📦",
        "color": "#f59e0b"
    },
    "Executaveis": {
        "extensions": [".exe", ".msi", ".bat", ".cmd", ".sh", ".app", ".deb", ".rpm", ".dmg"],
        "icon": "⚙️",
        "color": "#6b7280"
    },
    "Codigo": {
        "extensions": [".py", ".java", ".js", ".html", ".css", ".php", ".c", ".cpp", ".h", ".cs", ".json", ".xml", ".sql", ".r", ".go", ".rust", ".swift"],
        "icon": "💻",
        "color": "#059669"
    },
    "Fontes": {
        "extensions": [".ttf", ".otf", ".woff", ".woff2", ".eot"],
        "icon": "🔤",
        "color": "#dc2626"
    },
    "Ebooks": {
        "extensions": [".epub", ".mobi", ".azw", ".azw3", ".fb2"],
        "icon": "📚",
        "color": "#7c3aed"
    },
    "Outros": {
        "extensions": [],
        "icon": "📁",
        "color": "#64748b"
    }
}

# Temas disponíveis
THEMES = {
    "light": {
        "primary": "#3b82f6",
        "primary_dark": "#1d4ed8",
        "secondary": "#64748b",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "bg_primary": "#ffffff",
        "bg_secondary": "#f8fafc",
        "bg_card": "#f1f5f9",
        "text_primary": "#1e293b",
        "text_secondary": "#64748b",
        "border": "#e2e8f0"
    },
    "dark": {
        "primary": "#60a5fa",
        "primary_dark": "#3b82f6",
        "secondary": "#94a3b8",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#f87171",
        "bg_primary": "#0f172a",
        "bg_secondary": "#1e293b",
        "bg_card": "#334155",
        "text_primary": "#f1f5f9",
        "text_secondary": "#cbd5e1",
        "border": "#475569"
    }
}