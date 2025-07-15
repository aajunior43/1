# -*- coding: utf-8 -*-
"""
Interface gráfica principal melhorada com funcionalidades avançadas
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

from ..core.organizer import organizer
from ..core.filters import filter_manager, SizeFilter, DateFilter, ExtensionFilter
from ..utils.logger import logger
from ..utils.backup import backup_manager
from ..config.settings import config, THEMES

class AdvancedOrganizerGUI:
    """Interface gráfica avançada do organizador"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.setup_variables()
        self.setup_styles()
        self.create_widgets()
        self.setup_callbacks()
        
        # Estado da aplicação
        self.current_analysis = None
        self.current_suggestions = []
        self.is_analyzing = False
        self.is_organizing = False
        
        # Carregar configurações
        self.load_settings()
    
    def setup_window(self):
        """Configura a janela principal"""
        self.root.title("Organizador de Arquivos com IA - Versão Avançada")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Ícone da janela (se disponível)
        try:
            self.root.iconbitmap("assets/icon.ico")
        except:
            pass
        
        # Centralizar janela
        self.center_window()
    
    def center_window(self):
        """Centraliza a janela na tela"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_variables(self):
        """Configura variáveis da interface"""
        self.selected_folder = tk.StringVar()
        self.organization_mode = tk.StringVar(value="por_tipo")
        self.auto_backup = tk.BooleanVar(value=True)
        self.show_preview = tk.BooleanVar(value=True)
        self.current_theme = tk.StringVar(value="claro")
        
        # Variáveis de progresso
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Pronto")
        self.operation_var = tk.StringVar(value="")
    
    def setup_styles(self):
        """Configura estilos da interface"""
        self.style = ttk.Style()
        self.apply_theme("claro")
    
    def apply_theme(self, theme_name: str):
        """Aplica tema à interface"""
        if theme_name not in THEMES:
            theme_name = "claro"
        
        theme = THEMES[theme_name]
        
        # Configurar cores do tema
        self.root.configure(bg=theme["bg"])
        
        # Configurar estilos ttk
        self.style.theme_use("clam")
        
        # Configurar estilos personalizados
        self.style.configure("Title.TLabel", 
                           font=("Segoe UI", 16, "bold"),
                           background=theme["bg"],
                           foreground=theme["fg"])
        
        self.style.configure("Subtitle.TLabel",
                           font=("Segoe UI", 10, "bold"),
                           background=theme["bg"],
                           foreground=theme["fg"])
        
        self.style.configure("Custom.TButton",
                           font=("Segoe UI", 9),
                           padding=(10, 5))
        
        self.style.configure("Success.TButton",
                           font=("Segoe UI", 9, "bold"))
        
        self.style.configure("Warning.TButton",
                           font=("Segoe UI", 9))
    
    def create_widgets(self):
        """Cria todos os widgets da interface"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Criar seções
        self.create_header(main_frame)
        self.create_main_content(main_frame)
        self.create_footer(main_frame)
    
    def create_header(self, parent):
        """Cria cabeçalho da aplicação"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        
        # Título
        title_label = ttk.Label(header_frame, text="🗂️ Organizador de Arquivos com IA", 
                               style="Title.TLabel")
        title_label.grid(row=0, column=0, sticky="w")
        
        # Menu de configurações
        settings_frame = ttk.Frame(header_frame)
        settings_frame.grid(row=0, column=1, sticky="e")
        
        # Botão de tema
        theme_button = ttk.Button(settings_frame, text="🎨 Tema", 
                                 command=self.show_theme_menu)
        theme_button.grid(row=0, column=0, padx=(0, 5))
        
        # Botão de configurações
        config_button = ttk.Button(settings_frame, text="⚙️ Configurações", 
                                  command=self.show_settings)
        config_button.grid(row=0, column=1, padx=(0, 5))
        
        # Botão de ajuda
        help_button = ttk.Button(settings_frame, text="❓ Ajuda", 
                                command=self.show_help)
        help_button.grid(row=0, column=2)
    
    def create_main_content(self, parent):
        """Cria conteúdo principal"""
        # Painel esquerdo - Configurações
        left_panel = ttk.LabelFrame(parent, text="📋 Configurações", padding="10")
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        
        # Painel direito - Resultados
        right_panel = ttk.LabelFrame(parent, text="📊 Resultados", padding="10")
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        
        # Configurar expansão
        parent.columnconfigure(0, weight=1, minsize=400)
        parent.columnconfigure(1, weight=2, minsize=600)
        
        self.create_left_panel(left_panel)
        self.create_right_panel(right_panel)
    
    def create_left_panel(self, parent):
        """Cria painel esquerdo com configurações"""
        # Seleção de pasta
        folder_frame = ttk.LabelFrame(parent, text="📁 Pasta para Organizar", padding="10")
        folder_frame.pack(fill="x", pady=(0, 10))
        
        folder_entry = ttk.Entry(folder_frame, textvariable=self.selected_folder, 
                                font=("Segoe UI", 9), state="readonly")
        folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        browse_button = ttk.Button(folder_frame, text="📂 Selecionar", 
                                  command=self.select_folder, style="Custom.TButton")
        browse_button.pack(side="right")
        
        # Modo de organização
        mode_frame = ttk.LabelFrame(parent, text="🔧 Modo de Organização", padding="10")
        mode_frame.pack(fill="x", pady=(0, 10))
        
        modes = [
            ("por_tipo", "📄 Por Tipo de Arquivo"),
            ("por_data", "📅 Por Data de Modificação"),
            ("por_nome", "🔤 Por Nome (A-Z)"),
            ("personalizado", "⚙️ Personalizado")
        ]
        
        for value, text in modes:
            radio = ttk.Radiobutton(mode_frame, text=text, variable=self.organization_mode, 
                                   value=value, command=self.on_mode_change)
            radio.pack(anchor="w", pady=2)
        
        # Filtros avançados
        filters_frame = ttk.LabelFrame(parent, text="🔍 Filtros Avançados", padding="10")
        filters_frame.pack(fill="x", pady=(0, 10))
        
        # Botões de filtro
        filter_buttons_frame = ttk.Frame(filters_frame)
        filter_buttons_frame.pack(fill="x")
        
        ttk.Button(filter_buttons_frame, text="📏 Tamanho", 
                  command=self.add_size_filter).pack(side="left", padx=(0, 5))
        ttk.Button(filter_buttons_frame, text="📅 Data", 
                  command=self.add_date_filter).pack(side="left", padx=(0, 5))
        ttk.Button(filter_buttons_frame, text="📎 Extensão", 
                  command=self.add_extension_filter).pack(side="left")
        
        # Lista de filtros ativos
        self.filters_listbox = tk.Listbox(filters_frame, height=4, font=("Segoe UI", 8))
        self.filters_listbox.pack(fill="x", pady=(10, 0))
        
        # Botão para remover filtro
        ttk.Button(filters_frame, text="❌ Remover Filtro", 
                  command=self.remove_filter).pack(pady=(5, 0))
        
        # Opções adicionais
        options_frame = ttk.LabelFrame(parent, text="⚙️ Opções", padding="10")
        options_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Checkbutton(options_frame, text="💾 Criar backup automático", 
                       variable=self.auto_backup).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="👁️ Mostrar preview antes de aplicar", 
                       variable=self.show_preview).pack(anchor="w")
        
        # Botões de ação
        actions_frame = ttk.Frame(parent)
        actions_frame.pack(fill="x", pady=(10, 0))
        
        self.analyze_button = ttk.Button(actions_frame, text="🔍 Analisar Arquivos", 
                                        command=self.start_analysis, style="Custom.TButton")
        self.analyze_button.pack(fill="x", pady=(0, 5))
        
        self.preview_button = ttk.Button(actions_frame, text="👁️ Visualizar Preview", 
                                        command=self.show_preview_window, 
                                        style="Custom.TButton", state="disabled")
        self.preview_button.pack(fill="x", pady=(0, 5))
        
        self.organize_button = ttk.Button(actions_frame, text="✅ Aplicar Organização", 
                                         command=self.start_organization, 
                                         style="Success.TButton", state="disabled")
        self.organize_button.pack(fill="x", pady=(0, 5))
        
        self.cancel_button = ttk.Button(actions_frame, text="⏹️ Cancelar", 
                                       command=self.cancel_operation, 
                                       style="Warning.TButton", state="disabled")
        self.cancel_button.pack(fill="x")
    
    def create_right_panel(self, parent):
        """Cria painel direito com resultados"""
        # Notebook para abas
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True)
        
        # Aba de resultados
        self.create_results_tab()
        
        # Aba de estatísticas
        self.create_stats_tab()
        
        # Aba de logs
        self.create_logs_tab()
        
        # Aba de backups
        self.create_backups_tab()
    
    def create_results_tab(self):
        """Cria aba de resultados"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="📋 Resultados")
        
        # Toolbar
        toolbar = ttk.Frame(results_frame)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Button(toolbar, text="📤 Exportar", 
                  command=self.export_results).pack(side="left", padx=(0, 5))
        ttk.Button(toolbar, text="🔄 Atualizar", 
                  command=self.refresh_results).pack(side="left", padx=(0, 5))
        
        # Treeview para resultados
        columns = ("original", "categoria", "novo_nome", "pasta_destino", "tamanho")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=15)
        
        # Configurar colunas
        self.results_tree.heading("original", text="Arquivo Original")
        self.results_tree.heading("categoria", text="Categoria")
        self.results_tree.heading("novo_nome", text="Novo Nome")
        self.results_tree.heading("pasta_destino", text="Pasta Destino")
        self.results_tree.heading("tamanho", text="Tamanho (MB)")
        
        self.results_tree.column("original", width=200)
        self.results_tree.column("categoria", width=100)
        self.results_tree.column("novo_nome", width=200)
        self.results_tree.column("pasta_destino", width=150)
        self.results_tree.column("tamanho", width=80)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        h_scrollbar = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_tree.xview)
        
        self.results_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.results_tree.grid(row=1, column=0, sticky="nsew")
        v_scrollbar.grid(row=1, column=1, sticky="ns")
        h_scrollbar.grid(row=2, column=0, sticky="ew")
        
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)
    
    def create_stats_tab(self):
        """Cria aba de estatísticas"""
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="📊 Estatísticas")
        
        # Área de texto para estatísticas
        self.stats_text = tk.Text(stats_frame, wrap="word", font=("Consolas", 10), 
                                 state="disabled", bg="#f8f9fa")
        
        stats_scrollbar = ttk.Scrollbar(stats_frame, orient="vertical", command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scrollbar.set)
        
        self.stats_text.pack(side="left", fill="both", expand=True)
        stats_scrollbar.pack(side="right", fill="y")
    
    def create_logs_tab(self):
        """Cria aba de logs"""
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="📝 Logs")
        
        # Toolbar de logs
        logs_toolbar = ttk.Frame(logs_frame)
        logs_toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Button(logs_toolbar, text="🗑️ Limpar", 
                  command=self.clear_logs).pack(side="left", padx=(0, 5))
        ttk.Button(logs_toolbar, text="💾 Salvar", 
                  command=self.save_logs).pack(side="left", padx=(0, 5))
        ttk.Button(logs_toolbar, text="🔄 Atualizar", 
                  command=self.refresh_logs).pack(side="left")
        
        # Área de texto para logs
        self.logs_text = tk.Text(logs_frame, wrap="word", font=("Consolas", 9), 
                                state="disabled", bg="#1e1e1e", fg="#ffffff")
        
        logs_scrollbar = ttk.Scrollbar(logs_frame, orient="vertical", command=self.logs_text.yview)
        self.logs_text.configure(yscrollcommand=logs_scrollbar.set)
        
        self.logs_text.pack(side="left", fill="both", expand=True)
        logs_scrollbar.pack(side="right", fill="y")
    
    def create_backups_tab(self):
        """Cria aba de backups"""
        backups_frame = ttk.Frame(self.notebook)
        self.notebook.add(backups_frame, text="💾 Backups")
        
        # Toolbar de backups
        backups_toolbar = ttk.Frame(backups_frame)
        backups_toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Button(backups_toolbar, text="🔄 Atualizar", 
                  command=self.refresh_backups).pack(side="left", padx=(0, 5))
        ttk.Button(backups_toolbar, text="↩️ Restaurar", 
                  command=self.restore_backup).pack(side="left", padx=(0, 5))
        ttk.Button(backups_toolbar, text="🗑️ Excluir", 
                  command=self.delete_backup).pack(side="left")
        
        # Lista de backups
        columns = ("id", "data", "tipo", "arquivos", "tamanho")
        self.backups_tree = ttk.Treeview(backups_frame, columns=columns, show="headings")
        
        self.backups_tree.heading("id", text="ID")
        self.backups_tree.heading("data", text="Data/Hora")
        self.backups_tree.heading("tipo", text="Tipo")
        self.backups_tree.heading("arquivos", text="Arquivos")
        self.backups_tree.heading("tamanho", text="Tamanho")
        
        self.backups_tree.column("id", width=100)
        self.backups_tree.column("data", width=150)
        self.backups_tree.column("tipo", width=100)
        self.backups_tree.column("arquivos", width=80)
        self.backups_tree.column("tamanho", width=80)
        
        backups_scrollbar = ttk.Scrollbar(backups_frame, orient="vertical", 
                                         command=self.backups_tree.yview)
        self.backups_tree.configure(yscrollcommand=backups_scrollbar.set)
        
        self.backups_tree.pack(side="left", fill="both", expand=True)
        backups_scrollbar.pack(side="right", fill="y")
    
    def create_footer(self, parent):
        """Cria rodapé da aplicação"""
        footer_frame = ttk.Frame(parent)
        footer_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        footer_frame.columnconfigure(1, weight=1)
        
        # Barra de progresso
        progress_frame = ttk.Frame(footer_frame)
        progress_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        progress_frame.columnconfigure(1, weight=1)
        
        ttk.Label(progress_frame, text="Progresso:").grid(row=0, column=0, sticky="w")
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, length=300)
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        
        # Status
        status_frame = ttk.Frame(footer_frame)
        status_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        # Operação atual
        self.operation_label = ttk.Label(status_frame, textvariable=self.operation_var, 
                                        font=("Segoe UI", 8), foreground="gray")
        self.operation_label.grid(row=0, column=2, sticky="e")
        
        # Versão
        version_label = ttk.Label(footer_frame, text="v2.0.0 - Organizador Avançado", 
                                 font=("Segoe UI", 8), foreground="gray")
        version_label.grid(row=2, column=1, sticky="e")
    
    def setup_callbacks(self):
        """Configura callbacks do organizador"""
        organizer.set_progress_callback(self.update_progress)
        organizer.set_log_callback(self.add_log)
    
    # Métodos de interface
    def select_folder(self):
        """Seleciona pasta para organizar"""
        folder = filedialog.askdirectory(title="Selecionar pasta para organizar")
        if folder:
            self.selected_folder.set(folder)
            self.log(f"📁 Pasta selecionada: {folder}")
    
    def on_mode_change(self):
        """Callback para mudança de modo"""
        mode = self.organization_mode.get()
        if mode == "personalizado":
            self.show_custom_mode_dialog()
    
    def start_analysis(self):
        """Inicia análise da pasta"""
        if not self.selected_folder.get():
            messagebox.showwarning("Aviso", "Selecione uma pasta primeiro!")
            return
        
        if self.is_analyzing:
            return
        
        self.is_analyzing = True
        self.update_buttons_state()
        
        # Executar análise em thread separada
        thread = threading.Thread(target=self._analyze_thread)
        thread.daemon = True
        thread.start()
    
    def _analyze_thread(self):
        """Thread para análise"""
        try:
            self.status_var.set("Analisando...")
            
            result = organizer.analyze_folder(
                self.selected_folder.get(),
                self.organization_mode.get()
            )
            
            if result["success"]:
                self.current_analysis = result
                self.current_suggestions = result["suggestions"]
                
                # Atualizar interface na thread principal
                self.root.after(0, self._update_analysis_results)
            else:
                self.root.after(0, lambda: self._show_error("Erro na análise", 
                                                           result.get("error", "Erro desconhecido")))
        
        except Exception as e:
            self.root.after(0, lambda: self._show_error("Erro na análise", str(e)))
        
        finally:
            self.is_analyzing = False
            self.root.after(0, self.update_buttons_state)
    
    def _update_analysis_results(self):
        """Atualiza resultados da análise na interface"""
        if not self.current_analysis:
            return
        
        # Atualizar tabela de resultados
        self.update_results_table()
        
        # Atualizar estatísticas
        self.update_stats_display()
        
        # Atualizar status
        total_files = len(self.current_suggestions)
        self.status_var.set(f"Análise concluída: {total_files} arquivos")
        self.progress_var.set(0)
        
        # Habilitar botões
        self.preview_button.configure(state="normal")
        self.organize_button.configure(state="normal")
        
        self.log(f"✅ Análise concluída: {total_files} arquivos encontrados")
    
    def update_results_table(self):
        """Atualiza tabela de resultados"""
        # Limpar tabela
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Adicionar resultados
        for suggestion in self.current_suggestions:
            self.results_tree.insert("", "end", values=(
                suggestion["source_name"],
                suggestion["category"],
                suggestion["final_name"],
                suggestion["dest_folder_name"],
                f"{suggestion['size_mb']:.2f}"
            ))
    
    def update_stats_display(self):
        """Atualiza exibição de estatísticas"""
        if not self.current_analysis:
            return
        
        stats = self.current_analysis["stats"]
        
        stats_text = f"""
📊 ESTATÍSTICAS DA ANÁLISE
{'=' * 50}

📁 Total de arquivos: {stats['total_files']}
💾 Tamanho total: {stats['total_size_mb']:.2f} MB
📂 Categorias encontradas: {stats['categories_count']}

📋 DISTRIBUIÇÃO POR CATEGORIA:
{'-' * 30}
"""
        
        for category, info in stats["categories_stats"].items():
            stats_text += f"  {category}: {info['count']} arquivos ({info['size_mb']:.2f} MB)\n"
        
        if stats.get("largest_file"):
            largest = stats["largest_file"]
            stats_text += f"\n📈 Maior arquivo: {largest['name']} ({largest['size_mb']:.2f} MB)"
        
        if stats.get("smallest_file"):
            smallest = stats["smallest_file"]
            stats_text += f"\n📉 Menor arquivo: {smallest['name']} ({smallest['size_mb']:.2f} MB)"
        
        # Atualizar widget de texto
        self.stats_text.configure(state="normal")
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats_text)
        self.stats_text.configure(state="disabled")
    
    def start_organization(self):
        """Inicia organização dos arquivos"""
        if not self.current_suggestions:
            messagebox.showwarning("Aviso", "Execute a análise primeiro!")
            return
        
        if self.show_preview.get():
            if not self.confirm_organization():
                return
        
        self.is_organizing = True
        self.update_buttons_state()
        
        # Executar organização em thread separada
        thread = threading.Thread(target=self._organize_thread)
        thread.daemon = True
        thread.start()
    
    def _organize_thread(self):
        """Thread para organização"""
        try:
            self.root.after(0, lambda: self.status_var.set("Organizando arquivos..."))
            
            result = organizer.execute_organization(
                self.current_suggestions,
                self.auto_backup.get()
            )
            
            if result["success"]:
                self.root.after(0, lambda: self._show_organization_success(result))
            else:
                self.root.after(0, lambda: self._show_error("Erro na organização", 
                                                           result.get("error", "Erro desconhecido")))
        
        except Exception as e:
            self.root.after(0, lambda: self._show_error("Erro na organização", str(e)))
        
        finally:
            self.is_organizing = False
            self.root.after(0, self.update_buttons_state)
    
    def _show_organization_success(self, result):
        """Mostra resultado da organização"""
        stats = result["stats"]
        duration = result["duration_seconds"]
        
        message = f"""
✅ Organização concluída com sucesso!

📊 Resultados:
  • Arquivos movidos: {stats['moved_files']}
  • Erros: {stats['errors']}
  • Tempo total: {duration:.1f}s
"""
        
        if result.get("backup_id"):
            message += f"\n💾 Backup criado: {result['backup_id']}"
        
        messagebox.showinfo("Sucesso", message)
        
        self.status_var.set(f"Organização concluída: {stats['moved_files']} arquivos movidos")
        self.progress_var.set(0)
        
        # Limpar resultados
        self.current_analysis = None
        self.current_suggestions = []
        self.update_results_table()
        
        # Atualizar backups
        self.refresh_backups()
    
    def confirm_organization(self) -> bool:
        """Confirma organização com o usuário"""
        total_files = len(self.current_suggestions)
        
        message = f"""
🗂️ Confirmar Organização

Você está prestes a organizar {total_files} arquivos.

Esta operação irá:
• Mover os arquivos para suas pastas de destino
• Criar backup automático (se habilitado)
• Não pode ser desfeita facilmente

Deseja continuar?
"""
        
        return messagebox.askyesno("Confirmar Organização", message)
    
    def cancel_operation(self):
        """Cancela operação em andamento"""
        if self.is_analyzing or self.is_organizing:
            organizer.cancel_operation()
            self.status_var.set("Cancelando...")
    
    def update_buttons_state(self):
        """Atualiza estado dos botões"""
        if self.is_analyzing or self.is_organizing:
            self.analyze_button.configure(state="disabled")
            self.organize_button.configure(state="disabled")
            self.cancel_button.configure(state="normal")
        else:
            self.analyze_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            
            if self.current_suggestions:
                self.preview_button.configure(state="normal")
                self.organize_button.configure(state="normal")
            else:
                self.preview_button.configure(state="disabled")
                self.organize_button.configure(state="disabled")
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """Callback para atualização de progresso"""
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)
        
        if message:
            self.operation_var.set(message)
    
    def add_log(self, message: str):
        """Adiciona mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.logs_text.configure(state="normal")
        self.logs_text.insert(tk.END, log_message)
        self.logs_text.see(tk.END)
        self.logs_text.configure(state="disabled")
    
    def log(self, message: str):
        """Log interno da interface"""
        self.add_log(message)
        logger.info(message)
    
    # Métodos de filtros
    def add_size_filter(self):
        """Adiciona filtro de tamanho"""
        dialog = SizeFilterDialog(self.root)
        if dialog.result:
            min_size, max_size = dialog.result
            filter_obj = SizeFilter(min_size, max_size)
            filter_manager.add_filter(filter_obj)
            self.update_filters_display()
    
    def add_date_filter(self):
        """Adiciona filtro de data"""
        dialog = DateFilterDialog(self.root)
        if dialog.result:
            start_date, end_date = dialog.result
            filter_obj = DateFilter(start_date, end_date)
            filter_manager.add_filter(filter_obj)
            self.update_filters_display()
    
    def add_extension_filter(self):
        """Adiciona filtro de extensão"""
        extensions = simpledialog.askstring(
            "Filtro de Extensão",
            "Digite as extensões separadas por vírgula (ex: .jpg,.png,.gif):"
        )
        
        if extensions:
            ext_list = [ext.strip() for ext in extensions.split(",")]
            filter_obj = ExtensionFilter(ext_list)
            filter_manager.add_filter(filter_obj)
            self.update_filters_display()
    
    def remove_filter(self):
        """Remove filtro selecionado"""
        selection = self.filters_listbox.curselection()
        if selection:
            index = selection[0]
            filter_manager.remove_filter(index)
            self.update_filters_display()
    
    def update_filters_display(self):
        """Atualiza exibição de filtros"""
        self.filters_listbox.delete(0, tk.END)
        
        for i, filter_obj in enumerate(filter_manager.filters):
            self.filters_listbox.insert(tk.END, str(filter_obj))
    
    # Métodos de configuração
    def show_theme_menu(self):
        """Mostra menu de temas"""
        theme_window = ThemeSelectionDialog(self.root, self.current_theme.get())
        if theme_window.result:
            new_theme = theme_window.result
            self.current_theme.set(new_theme)
            self.apply_theme(new_theme)
            config.set("theme", new_theme)
    
    def show_settings(self):
        """Mostra janela de configurações"""
        SettingsDialog(self.root)
    
    def show_help(self):
        """Mostra janela de ajuda"""
        HelpDialog(self.root)
    
    def show_custom_mode_dialog(self):
        """Mostra diálogo para modo personalizado"""
        CustomModeDialog(self.root)
    
    def show_preview_window(self):
        """Mostra janela de preview"""
        if self.current_analysis:
            PreviewDialog(self.root, self.current_analysis)
    
    # Métodos de exportação e backup
    def export_results(self):
        """Exporta resultados para arquivo"""
        if not self.current_suggestions:
            messagebox.showwarning("Aviso", "Nenhum resultado para exportar!")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Salvar resultados",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump({
                        "analysis": self.current_analysis,
                        "suggestions": self.current_suggestions,
                        "export_date": datetime.now().isoformat()
                    }, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Sucesso", f"Resultados exportados para {filename}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")
    
    def refresh_results(self):
        """Atualiza exibição de resultados"""
        self.update_results_table()
    
    def clear_logs(self):
        """Limpa logs"""
        self.logs_text.configure(state="normal")
        self.logs_text.delete(1.0, tk.END)
        self.logs_text.configure(state="disabled")
    
    def save_logs(self):
        """Salva logs em arquivo"""
        filename = filedialog.asksaveasfilename(
            title="Salvar logs",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                logs_content = self.logs_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(logs_content)
                
                messagebox.showinfo("Sucesso", f"Logs salvos em {filename}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar logs: {str(e)}")
    
    def refresh_logs(self):
        """Atualiza logs"""
        # Carregar logs do arquivo
        try:
            recent_logs = logger.get_recent_logs(100)
            
            self.logs_text.configure(state="normal")
            self.logs_text.delete(1.0, tk.END)
            
            for log_entry in recent_logs:
                self.logs_text.insert(tk.END, f"{log_entry}\n")
            
            self.logs_text.see(tk.END)
            self.logs_text.configure(state="disabled")
            
        except Exception as e:
            self.log(f"Erro ao carregar logs: {str(e)}")
    
    def refresh_backups(self):
        """Atualiza lista de backups"""
        # Limpar lista
        for item in self.backups_tree.get_children():
            self.backups_tree.delete(item)
        
        # Carregar backups
        try:
            backups = backup_manager.list_backups()
            
            for backup in backups:
                self.backups_tree.insert("", "end", values=(
                    backup["id"][:8],  # ID abreviado
                    backup["timestamp"],
                    backup["data"].get("type", "unknown"),
                    len(backup["data"].get("files_moved", [])),
                    f"{backup.get('size_mb', 0):.1f} MB"
                ))
                
        except Exception as e:
            self.log(f"Erro ao carregar backups: {str(e)}")
    
    def restore_backup(self):
        """Restaura backup selecionado"""
        selection = self.backups_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um backup para restaurar!")
            return
        
        item = self.backups_tree.item(selection[0])
        backup_id = item["values"][0]
        
        # Confirmar restauração
        if messagebox.askyesno("Confirmar Restauração", 
                              f"Deseja restaurar o backup {backup_id}?\n\n"
                              "Esta operação irá desfazer as mudanças feitas."):
            try:
                success = backup_manager.restore_backup(backup_id)
                if success:
                    messagebox.showinfo("Sucesso", "Backup restaurado com sucesso!")
                else:
                    messagebox.showerror("Erro", "Falha ao restaurar backup")
                    
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao restaurar backup: {str(e)}")
    
    def delete_backup(self):
        """Exclui backup selecionado"""
        selection = self.backups_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um backup para excluir!")
            return
        
        item = self.backups_tree.item(selection[0])
        backup_id = item["values"][0]
        
        # Confirmar exclusão
        if messagebox.askyesno("Confirmar Exclusão", 
                              f"Deseja excluir o backup {backup_id}?\n\n"
                              "Esta operação não pode ser desfeita."):
            try:
                success = backup_manager.delete_backup(backup_id)
                if success:
                    self.refresh_backups()
                    messagebox.showinfo("Sucesso", "Backup excluído com sucesso!")
                else:
                    messagebox.showerror("Erro", "Falha ao excluir backup")
                    
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao excluir backup: {str(e)}")
    
    # Métodos de configuração
    def load_settings(self):
        """Carrega configurações salvas"""
        try:
            # Carregar tema
            theme = config.get("theme", "claro")
            self.current_theme.set(theme)
            self.apply_theme(theme)
            
            # Carregar outras configurações
            self.auto_backup.set(config.get("auto_backup", True))
            self.show_preview.set(config.get("show_preview", True))
            
            # Atualizar filtros
            self.update_filters_display()
            
            # Carregar logs e backups
            self.refresh_logs()
            self.refresh_backups()
            
        except Exception as e:
            self.log(f"Erro ao carregar configurações: {str(e)}")
    
    def save_settings(self):
        """Salva configurações atuais"""
        try:
            config.set("theme", self.current_theme.get())
            config.set("auto_backup", self.auto_backup.get())
            config.set("show_preview", self.show_preview.get())
            config.save()
            
        except Exception as e:
            self.log(f"Erro ao salvar configurações: {str(e)}")
    
    def _show_error(self, title: str, message: str):
        """Mostra erro na interface"""
        messagebox.showerror(title, message)
        self.status_var.set("Erro")
        self.progress_var.set(0)
    
    def run(self):
        """Executa a aplicação"""
        try:
            self.log("🚀 Organizador de Arquivos com IA iniciado")
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
            
        except Exception as e:
            logger.error("Erro na execução da aplicação", e)
            messagebox.showerror("Erro Crítico", f"Erro na aplicação: {str(e)}")
    
    def on_closing(self):
        """Callback para fechamento da aplicação"""
        try:
            # Cancelar operações em andamento
            if self.is_analyzing or self.is_organizing:
                organizer.cancel_operation()
            
            # Salvar configurações
            self.save_settings()
            
            self.log("👋 Organizador de Arquivos com IA finalizado")
            
        except Exception as e:
            logger.error("Erro ao fechar aplicação", e)
        
        finally:
            self.root.destroy()

# Diálogos auxiliares (implementação simplificada)
class SizeFilterDialog:
    def __init__(self, parent):
        self.result = None
        # Implementação simplificada
        min_size = simpledialog.askfloat("Filtro de Tamanho", "Tamanho mínimo (MB):", minvalue=0)
        if min_size is not None:
            max_size = simpledialog.askfloat("Filtro de Tamanho", "Tamanho máximo (MB):", minvalue=min_size)
            if max_size is not None:
                self.result = (min_size, max_size)

class DateFilterDialog:
    def __init__(self, parent):
        self.result = None
        # Implementação simplificada - usar datas padrão
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        self.result = (start_date, end_date)

class ThemeSelectionDialog:
    def __init__(self, parent, current_theme):
        self.result = None
        themes = list(THEMES.keys())
        # Implementação simplificada
        self.result = current_theme  # Manter tema atual por enquanto

class SettingsDialog:
    def __init__(self, parent):
        # Implementação simplificada
        messagebox.showinfo("Configurações", "Janela de configurações em desenvolvimento")

class HelpDialog:
    def __init__(self, parent):
        help_text = """
🗂️ ORGANIZADOR DE ARQUIVOS COM IA - AJUDA

📋 COMO USAR:
1. Selecione uma pasta para organizar
2. Escolha o modo de organização
3. Configure filtros (opcional)
4. Clique em "Analisar Arquivos"
5. Revise os resultados
6. Clique em "Aplicar Organização"

🔧 MODOS DE ORGANIZAÇÃO:
• Por Tipo: Organiza por categoria de arquivo
• Por Data: Organiza por data de modificação
• Por Nome: Organiza alfabeticamente
• Personalizado: Regras customizadas

🔍 FILTROS AVANÇADOS:
• Tamanho: Filtra por tamanho do arquivo
• Data: Filtra por data de modificação
• Extensão: Filtra por tipo de arquivo

💾 BACKUPS:
• Backups automáticos são criados
• Podem ser restaurados a qualquer momento
• Limpeza automática de backups antigos

⚙️ CONFIGURAÇÕES:
• Temas claro e escuro
• Configurações de backup
• Filtros personalizados
"""
        messagebox.showinfo("Ajuda", help_text)

class CustomModeDialog:
    def __init__(self, parent):
        # Implementação simplificada
        messagebox.showinfo("Modo Personalizado", "Modo personalizado em desenvolvimento")

class PreviewDialog:
    def __init__(self, parent, analysis):
        # Implementação simplificada
        preview = organizer.preview_organization(
            analysis["suggestions"][0]["source"] if analysis["suggestions"] else "",
            "por_tipo"
        )
        
        if preview["success"]:
            structure = preview["preview_structure"]
            preview_text = "📁 PREVIEW DA ORGANIZAÇÃO:\n\n"
            
            for folder, files in structure.items():
                preview_text += f"📂 {folder}/\n"
                for file_info in files[:5]:  # Mostrar apenas 5 arquivos por pasta
                    preview_text += f"  📄 {file_info['name']} ({file_info['size_mb']:.2f} MB)\n"
                if len(files) > 5:
                    preview_text += f"  ... e mais {len(files) - 5} arquivos\n"
                preview_text += "\n"
            
            messagebox.showinfo("Preview da Organização", preview_text)
        else:
            messagebox.showerror("Erro", "Erro ao gerar preview")

def main():
    """Função principal"""
    try:
        app = AdvancedOrganizerGUI()
        app.run()
    except Exception as e:
        logger.error("Erro crítico na aplicação", e)
        messagebox.showerror("Erro Crítico", f"Erro ao iniciar aplicação: {str(e)}")

if __name__ == "__main__":
    main()