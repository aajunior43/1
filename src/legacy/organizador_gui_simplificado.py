import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter.font import Font
import threading
import json
from pathlib import Path
import os
import shutil
import datetime

class OrganizadorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.pasta_selecionada = None
        self.sugestoes = []
        self.processando = False
        
        # Cores modernas
        self.cores = {
            'primary': '#3b82f6',      # Azul moderno
            'primary_dark': '#1d4ed8', # Azul escuro
            'secondary': '#64748b',    # Cinza azulado
            'success': '#10b981',      # Verde
            'warning': '#f59e0b',      # Amarelo
            'danger': '#ef4444',       # Vermelho
            'bg_primary': '#ffffff',   # Fundo branco
            'bg_secondary': '#f8fafc', # Fundo secundário
            'bg_card': '#f1f5f9',      # Fundo dos cards
            'text_primary': '#1e293b', # Texto principal
            'text_secondary': '#64748b', # Texto secundário
            'border': '#e2e8f0'        # Bordas
        }
        
        self.configurar_janela()
        self.configurar_estilo()
        self.criar_widgets()
        
    def configurar_janela(self):
        """Configura a janela principal com design moderno"""
        self.root.title("📁 Organizador de Arquivos")
        self.root.geometry("1100x800")
        self.root.minsize(1000, 700)
        self.root.configure(bg=self.cores['bg_primary'])
        
        # Centralizar janela
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1100 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"1100x800+{x}+{y}")
        
        # Fontes modernas
        self.font_titulo = Font(family="Segoe UI", size=24, weight="bold")
        self.font_subtitulo = Font(family="Segoe UI", size=16, weight="bold")
        self.font_normal = Font(family="Segoe UI", size=11)
        self.font_small = Font(family="Segoe UI", size=9)
        
    def configurar_estilo(self):
        """Configura estilos modernos para os widgets"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Estilo para Notebook
        self.style.configure('Modern.TNotebook', 
                           background=self.cores['bg_primary'],
                           borderwidth=0)
        self.style.configure('Modern.TNotebook.Tab',
                           padding=[20, 12],
                           font=self.font_normal,
                           background=self.cores['bg_secondary'],
                           foreground=self.cores['text_primary'])
        self.style.map('Modern.TNotebook.Tab',
                      background=[('selected', self.cores['primary']),
                                ('active', self.cores['bg_card'])],
                      foreground=[('selected', 'white')])
        
        # Estilo para Buttons
        self.style.configure('Primary.TButton',
                           font=self.font_normal,
                           padding=[15, 8],
                           background=self.cores['primary'],
                           foreground='white',
                           borderwidth=0,
                           focuscolor='none')
        self.style.map('Primary.TButton',
                      background=[('active', self.cores['primary_dark'])])
        
        self.style.configure('Success.TButton',
                           font=self.font_normal,
                           padding=[15, 8],
                           background=self.cores['success'],
                           foreground='white',
                           borderwidth=0,
                           focuscolor='none')
        
        self.style.configure('Warning.TButton',
                           font=self.font_normal,
                           padding=[15, 8],
                           background=self.cores['warning'],
                           foreground='white',
                           borderwidth=0,
                           focuscolor='none')
        
        # Estilo para Entry
        self.style.configure('Modern.TEntry',
                           padding=[10, 8],
                           font=self.font_normal,
                           borderwidth=1,
                           relief='solid')
        
        # Estilo para Frames
        self.style.configure('Card.TFrame',
                           background=self.cores['bg_card'],
                           relief='solid',
                           borderwidth=1)
        
    def criar_widgets(self):
        """Cria todos os widgets da interface moderna"""
        # Header
        self.criar_header()
        
        # Container principal
        self.main_container = tk.Frame(self.root, bg=self.cores['bg_primary'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Notebook moderno
        self.notebook = ttk.Notebook(self.main_container, style='Modern.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Abas
        self.criar_aba_selecao()
        self.criar_aba_organizacao()
        self.criar_aba_resultados()
        
        # Footer
        self.criar_footer()
        
    def criar_header(self):
        """Cria o cabeçalho moderno"""
        header = tk.Frame(self.root, bg=self.cores['primary'], height=100)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Container do header
        header_content = tk.Frame(header, bg=self.cores['primary'])
        header_content.pack(expand=True, fill=tk.BOTH, padx=30, pady=20)
        
        # Título principal
        titulo = tk.Label(
            header_content,
            text="📁 Organizador de Arquivos",
            font=self.font_titulo,
            bg=self.cores['primary'],
            fg='white'
        )
        titulo.pack(anchor=tk.W)
        
        # Subtítulo
        subtitulo = tk.Label(
            header_content,
            text="Organize seus arquivos de forma simples e eficiente",
            font=self.font_normal,
            bg=self.cores['primary'],
            fg='white'
        )
        subtitulo.pack(anchor=tk.W, pady=(5, 0))
        
    def criar_aba_selecao(self):
        """Cria a aba de seleção moderna"""
        selecao_frame = tk.Frame(self.notebook, bg=self.cores['bg_primary'])
        self.notebook.add(selecao_frame, text="📁  Seleção")
        
        main_selecao = tk.Frame(selecao_frame, bg=self.cores['bg_primary'])
        main_selecao.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Card de seleção de pasta
        pasta_card = tk.Frame(main_selecao, bg=self.cores['bg_card'], relief='solid', borderwidth=1)
        pasta_card.pack(fill=tk.X, pady=(0, 20))
        
        pasta_content = tk.Frame(pasta_card, bg=self.cores['bg_card'])
        pasta_content.pack(fill=tk.X, padx=25, pady=25)
        
        tk.Label(
            pasta_content,
            text="📂 Seleção da Pasta",
            font=self.font_subtitulo,
            bg=self.cores['bg_card'],
            fg=self.cores['text_primary']
        ).pack(anchor=tk.W, pady=(0, 15))
        
        self.pasta_var = tk.StringVar(value="Nenhuma pasta selecionada")
        
        pasta_display_frame = tk.Frame(pasta_content, bg=self.cores['bg_secondary'], relief='solid', borderwidth=1)
        pasta_display_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.pasta_label = tk.Label(
            pasta_display_frame,
            textvariable=self.pasta_var,
            font=self.font_normal,
            bg=self.cores['bg_secondary'],
            fg=self.cores['primary'],
            wraplength=800,
            justify=tk.LEFT
        )
        self.pasta_label.pack(anchor=tk.W, padx=15, pady=10)
        
        ttk.Button(
            pasta_content,
            text="🔍 Selecionar Pasta",
            command=self.selecionar_pasta,
            style='Primary.TButton'
        ).pack(anchor=tk.W)
        
        # Card de modo de operação
        modo_card = tk.Frame(main_selecao, bg=self.cores['bg_card'], relief='solid', borderwidth=1)
        modo_card.pack(fill=tk.X, pady=(0, 20))
        
        modo_content = tk.Frame(modo_card, bg=self.cores['bg_card'])
        modo_content.pack(fill=tk.X, padx=25, pady=25)
        
        tk.Label(
            modo_content,
            text="⚙️ Modo de Organização",
            font=self.font_subtitulo,
            bg=self.cores['bg_card'],
            fg=self.cores['text_primary']
        ).pack(anchor=tk.W, pady=(0, 15))
        
        self.modo_var = tk.StringVar(value="por_tipo")
        
        # Opções de modo
        modo_frame = tk.Frame(modo_content, bg=self.cores['bg_card'])
        modo_frame.pack(fill=tk.X)
        
        tk.Radiobutton(
            modo_frame,
            text="📁 Organizar por Tipo de Arquivo",
            variable=self.modo_var,
            value="por_tipo",
            font=self.font_normal,
            bg=self.cores['bg_card'],
            fg=self.cores['text_primary'],
            selectcolor=self.cores['bg_secondary']
        ).pack(anchor=tk.W, pady=(0, 5))
        
        tk.Radiobutton(
            modo_frame,
            text="📅 Organizar por Data",
            variable=self.modo_var,
            value="por_data",
            font=self.font_normal,
            bg=self.cores['bg_card'],
            fg=self.cores['text_primary'],
            selectcolor=self.cores['bg_secondary']
        ).pack(anchor=tk.W, pady=(0, 5))
        
        tk.Radiobutton(
            modo_frame,
            text="🔤 Organizar por Nome (A-Z)",
            variable=self.modo_var,
            value="por_nome",
            font=self.font_normal,
            bg=self.cores['bg_card'],
            fg=self.cores['text_primary'],
            selectcolor=self.cores['bg_secondary']
        ).pack(anchor=tk.W)
        
    def criar_aba_organizacao(self):
        """Cria a aba de organização"""
        organizacao_frame = tk.Frame(self.notebook, bg=self.cores['bg_primary'])
        self.notebook.add(organizacao_frame, text="🔍  Organização")
        
        main_organizacao = tk.Frame(organizacao_frame, bg=self.cores['bg_primary'])
        main_organizacao.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Card de controle
        controle_card = tk.Frame(main_organizacao, bg=self.cores['bg_card'], relief='solid', borderwidth=1)
        controle_card.pack(fill=tk.X, pady=(0, 20))
        
        controle_content = tk.Frame(controle_card, bg=self.cores['bg_card'])
        controle_content.pack(fill=tk.X, padx=25, pady=25)
        
        tk.Label(
            controle_content,
            text="🚀 Iniciar Organização",
            font=self.font_subtitulo,
            bg=self.cores['bg_card'],
            fg=self.cores['text_primary']
        ).pack(anchor=tk.W, pady=(0, 15))
        
        btn_frame = tk.Frame(controle_content, bg=self.cores['bg_card'])
        btn_frame.pack(fill=tk.X)
        
        self.btn_organizar = ttk.Button(
            btn_frame,
            text="🔍 Analisar Arquivos",
            command=self.iniciar_organizacao,
            style='Primary.TButton'
        )
        self.btn_organizar.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_parar = ttk.Button(
            btn_frame,
            text="⏹️ Parar",
            command=self.parar_organizacao,
            style='Warning.TButton',
            state='disabled'
        )
        self.btn_parar.pack(side=tk.LEFT)
        
        # Card de progresso
        progresso_card = tk.Frame(main_organizacao, bg=self.cores['bg_card'], relief='solid', borderwidth=1)
        progresso_card.pack(fill=tk.X, pady=(0, 20))
        
        progresso_content = tk.Frame(progresso_card, bg=self.cores['bg_card'])
        progresso_content.pack(fill=tk.X, padx=25, pady=25)
        
        tk.Label(
            progresso_content,
            text="📊 Progresso",
            font=self.font_subtitulo,
            bg=self.cores['bg_card'],
            fg=self.cores['text_primary']
        ).pack(anchor=tk.W, pady=(0, 15))
        
        self.progress = ttk.Progressbar(
            progresso_content,
            mode='determinate',
            length=400
        )
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_var = tk.StringVar(value="Aguardando...")
        self.progress_label = tk.Label(
            progresso_content,
            textvariable=self.progress_var,
            font=self.font_normal,
            bg=self.cores['bg_card'],
            fg=self.cores['text_secondary']
        )
        self.progress_label.pack(anchor=tk.W)
        
        # Card de log
        log_card = tk.Frame(main_organizacao, bg=self.cores['bg_card'], relief='solid', borderwidth=1)
        log_card.pack(fill=tk.BOTH, expand=True)
        
        log_content = tk.Frame(log_card, bg=self.cores['bg_card'])
        log_content.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        tk.Label(
            log_content,
            text="📝 Log de Atividades",
            font=self.font_subtitulo,
            bg=self.cores['bg_card'],
            fg=self.cores['text_primary']
        ).pack(anchor=tk.W, pady=(0, 15))
        
        self.log_text = scrolledtext.ScrolledText(
            log_content,
            height=15,
            font=self.font_small,
            bg='white',
            fg=self.cores['text_primary'],
            relief='solid',
            borderwidth=1
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
    def criar_aba_resultados(self):
        """Cria a aba de resultados moderna"""
        resultados_frame = tk.Frame(self.notebook, bg=self.cores['bg_primary'])
        self.notebook.add(resultados_frame, text="📋  Resultados")
        
        main_resultados = tk.Frame(resultados_frame, bg=self.cores['bg_primary'])
        main_resultados.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Card de controles
        controles_card = tk.Frame(main_resultados, bg=self.cores['bg_card'], relief='solid', borderwidth=1)
        controles_card.pack(fill=tk.X, pady=(0, 20))
        
        controles_content = tk.Frame(controles_card, bg=self.cores['bg_card'])
        controles_content.pack(fill=tk.X, padx=25, pady=25)
        
        tk.Label(
            controles_content,
            text="⚡ Ações",
            font=self.font_subtitulo,
            bg=self.cores['bg_card'],
            fg=self.cores['text_primary']
        ).pack(anchor=tk.W, pady=(0, 15))
        
        btn_resultados_frame = tk.Frame(controles_content, bg=self.cores['bg_card'])
        btn_resultados_frame.pack(fill=tk.X)
        
        self.btn_aplicar = ttk.Button(
            btn_resultados_frame,
            text="✅ Aplicar Mudanças",
            command=self.aplicar_mudancas,
            style='Success.TButton',
            state='disabled'
        )
        self.btn_aplicar.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_exportar = ttk.Button(
            btn_resultados_frame,
            text="📤 Exportar Log",
            command=self.exportar_log,
            style='Primary.TButton',
            state='disabled'
        )
        self.btn_exportar.pack(side=tk.LEFT)
        
        # Card de resultados
        resultados_card = tk.Frame(main_resultados, bg=self.cores['bg_card'], relief='solid', borderwidth=1)
        resultados_card.pack(fill=tk.BOTH, expand=True)
        
        resultados_content = tk.Frame(resultados_card, bg=self.cores['bg_card'])
        resultados_content.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        tk.Label(
            resultados_content,
            text="📊 Arquivos Organizados",
            font=self.font_subtitulo,
            bg=self.cores['bg_card'],
            fg=self.cores['text_primary']
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Treeview para resultados
        tree_frame = tk.Frame(resultados_content, bg=self.cores['bg_card'])
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(
            tree_frame,
            columns=('arquivo', 'categoria', 'novo_nome', 'pasta_destino'),
            show='headings',
            height=15
        )
        
        # Configurar colunas
        self.tree.heading('arquivo', text='Arquivo Original')
        self.tree.heading('categoria', text='Categoria')
        self.tree.heading('novo_nome', text='Novo Nome')
        self.tree.heading('pasta_destino', text='Pasta Destino')
        
        self.tree.column('arquivo', width=250)
        self.tree.column('categoria', width=150)
        self.tree.column('novo_nome', width=250)
        self.tree.column('pasta_destino', width=200)
        
        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll_y.pack(side="right", fill="y")
        tree_scroll_x.pack(side="bottom", fill="x")
        
    def criar_footer(self):
        """Cria o rodapé moderno"""
        footer = tk.Frame(self.root, bg=self.cores['bg_secondary'], height=40)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        
        self.status_var = tk.StringVar(value="Pronto para começar")
        status_label = tk.Label(
            footer,
            textvariable=self.status_var,
            font=self.font_small,
            bg=self.cores['bg_secondary'],
            fg=self.cores['text_secondary'],
            anchor=tk.W
        )
        status_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        # Versão
        versao_label = tk.Label(
            footer,
            text="v1.0 - Organizador de Arquivos",
            font=self.font_small,
            bg=self.cores['bg_secondary'],
            fg=self.cores['text_secondary']
        )
        versao_label.pack(side=tk.RIGHT, padx=20, pady=10)
        
    def log(self, mensagem):
        """Adiciona mensagem ao log"""
        self.log_text.insert(tk.END, f"{mensagem}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def atualizar_status(self, status):
        """Atualiza a barra de status"""
        self.status_var.set(status)
        self.root.update_idletasks()
        
    def selecionar_pasta(self):
        """Seleciona pasta para análise"""
        pasta = filedialog.askdirectory(title="Selecione a pasta para organizar")
        if pasta:
            self.pasta_selecionada = pasta
            self.pasta_var.set(pasta)
            self.atualizar_status(f"Pasta selecionada: {pasta}")
            self.log(f"📁 Pasta selecionada: {pasta}")
            
    def iniciar_organizacao(self):
        """Inicia a organização dos arquivos"""
        if not self.pasta_selecionada:
            messagebox.showerror("Erro", "Por favor, selecione uma pasta primeiro")
            return
            
        self.processando = True
        self.btn_organizar.config(state='disabled')
        self.btn_parar.config(state='normal')
        self.progress.start()
        self.progress_var.set("Iniciando organização...")
        
        # Limpar resultados anteriores
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.log("🚀 Iniciando organização...")
        
        def organizar():
            try:
                # Obter modo de organização
                modo = self.modo_var.get()
                
                # Listar arquivos
                pasta_origem = Path(self.pasta_selecionada)
                arquivos = list(pasta_origem.glob('*'))
                arquivos = [a for a in arquivos if a.is_file()]
                
                if not arquivos:
                    self.root.after(0, lambda: self.log("⚠️ Nenhum arquivo encontrado para organizar."))
                    return
                
                self.root.after(0, lambda: self.log(f"🔍 Encontrados {len(arquivos)} arquivos para organização"))
                self.root.after(0, lambda: self.progress_var.set(f"Processando {len(arquivos)} arquivos..."))
                
                # Configurar progresso
                self.root.after(0, lambda: self.progress.configure(mode='determinate', maximum=len(arquivos), value=0))
                
                # Processar arquivos
                self.sugestoes = []
                for i, arquivo in enumerate(arquivos, 1):
                    if not self.processando:  # Verificar se foi interrompido
                        break
                        
                    # Atualizar progresso
                    self.root.after(0, lambda i=i, total=len(arquivos): self.progress.configure(value=i))
                    self.root.after(0, lambda p=f"[{i}/{len(arquivos)}] Processando: {arquivo.name}": self.progress_var.set(p))
                    self.root.after(0, lambda a=arquivo, i=i, total=len(arquivos): 
                                   self.log(f"📄 [{i:3d}/{total}] Processando: {a.name}"))
                    
                    # Determinar categoria e pasta destino
                    if modo == "por_tipo":
                        categoria = self.obter_categoria_por_extensao(arquivo.suffix)
                        pasta_destino = pasta_origem / categoria
                    elif modo == "por_data":
                        data_modificacao = datetime.datetime.fromtimestamp(arquivo.stat().st_mtime)
                        categoria = f"{data_modificacao.year}-{data_modificacao.month:02d}"
                        pasta_destino = pasta_origem / categoria
                    else:  # por_nome
                        primeira_letra = arquivo.stem[0].upper() if arquivo.stem else "#"
                        if not primeira_letra.isalpha():
                            primeira_letra = "#"
                        categoria = primeira_letra
                        pasta_destino = pasta_origem / categoria
                    
                    # Criar sugestão
                    nome_final = arquivo.name
                    caminho_final = pasta_destino / nome_final
                    
                    # Verificar se já existe arquivo com mesmo nome
                    if pasta_destino.exists() and (pasta_destino / nome_final).exists():
                        nome_base = arquivo.stem
                        extensao = arquivo.suffix
                        contador = 1
                        while (pasta_destino / f"{nome_base}_{contador}{extensao}").exists():
                            contador += 1
                        nome_final = f"{nome_base}_{contador}{extensao}"
                        caminho_final = pasta_destino / nome_final
                    
                    sugestao = {
                        'arquivo_original': str(arquivo),
                        'nome_original': arquivo.name,
                        'caminho_final': str(caminho_final),
                        'nome_final': nome_final,
                        'categoria': categoria,
                        'pasta_destino': str(pasta_destino)
                    }
                    
                    self.sugestoes.append(sugestao)
                    self.root.after(0, lambda: self.log(f"    ✅ Será movido para: {categoria}/"))
                
                # Estatísticas finais
                self.root.after(0, lambda: self.log("\n✅ Análise concluída!"))
                self.root.after(0, lambda: self.log("=" * 60))
                self.root.after(0, lambda: self.log("📊 ESTATÍSTICAS FINAIS:"))
                self.root.after(0, lambda: self.log(f"   📄 Total de arquivos: {len(arquivos)}"))
                
                # Categorias encontradas
                categorias = set(s['categoria'] for s in self.sugestoes)
                self.root.after(0, lambda: self.log(f"   📁 Categorias detectadas: {len(categorias)}"))
                
                if categorias:
                    self.root.after(0, lambda: self.log("   🏷️  Categorias encontradas:"))
                    for categoria in sorted(categorias):
                        self.root.after(0, lambda c=categoria: self.log(f"      • {c}"))
                
                self.root.after(0, lambda: self.log("=" * 60))
                
                # Atualizar interface
                self.root.after(0, self.atualizar_resultados)
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Erro na organização: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro na organização: {str(e)}"))
            finally:
                self.root.after(0, self.finalizar_organizacao)
                
        threading.Thread(target=organizar, daemon=True).start()
    
    def obter_categoria_por_extensao(self, extensao):
        """Retorna a categoria baseada na extensão do arquivo"""
        extensao = extensao.lower()
        
        # Imagens
        if extensao in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'):
            return "Imagens"
        
        # Documentos
        if extensao in ('.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'):
            return "Documentos"
        
        # Vídeos
        if extensao in ('.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v'):
            return "Videos"
        
        # Áudio
        if extensao in ('.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma', '.m4a'):
            return "Audio"
        
        # Compactados
        if extensao in ('.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'):
            return "Compactados"
        
        # Executáveis
        if extensao in ('.exe', '.msi', '.bat', '.cmd', '.sh', '.app'):
            return "Executaveis"
        
        # Código
        if extensao in ('.py', '.java', '.js', '.html', '.css', '.php', '.c', '.cpp', '.h', '.cs', '.json', '.xml'):
            return "Codigo"
        
        return "Outros"
    
    def atualizar_resultados(self):
        """Atualiza a exibição dos resultados"""
        for sugestao in self.sugestoes:
            # Extrair nome do arquivo original
            arquivo_original = Path(sugestao.get('arquivo_original', '')).name
            
            self.tree.insert('', 'end', values=(
                arquivo_original,
                sugestao.get('categoria', ''),
                sugestao.get('nome_final', ''),
                Path(sugestao.get('pasta_destino', '')).name
            ))
            
        self.log(f"✅ Análise concluída! {len(self.sugestoes)} arquivos analisados")
        self.btn_aplicar.config(state='normal')
        self.btn_exportar.config(state='normal')
        
        # Mudar para aba de resultados
        self.notebook.select(2)
        
    def finalizar_organizacao(self):
        """Finaliza o processo de organização"""
        self.processando = False
        self.btn_organizar.config(state='normal')
        self.btn_parar.config(state='disabled')
        self.progress.stop()
        self.progress_var.set("Organização concluída")
        self.atualizar_status("Organização concluída")
        
    def parar_organizacao(self):
        """Para a organização em andamento"""
        self.processando = False
        self.finalizar_organizacao()
        self.log("⏹️ Organização interrompida pelo usuário")
        
    def aplicar_mudancas(self):
        """Aplica as mudanças sugeridas"""
        if not self.sugestoes:
            messagebox.showwarning("Aviso", "Nenhuma sugestão para aplicar")
            return
            
        resposta = messagebox.askyesno(
            "Confirmar",
            f"Deseja aplicar as mudanças em {len(self.sugestoes)} arquivos?\n\nEsta ação não pode ser desfeita."
        )
        
        if resposta:
            self.log("🔄 Aplicando mudanças...")
            self.atualizar_status("Aplicando mudanças...")
            
            def aplicar():
                try:
                    # Configurar progresso
                    self.root.after(0, lambda: self.progress.configure(mode='determinate', maximum=len(self.sugestoes), value=0))
                    
                    # Aplicar mudanças
                    for i, sugestao in enumerate(self.sugestoes, 1):
                        arquivo_original = Path(sugestao['arquivo_original'])
                        pasta_destino = Path(sugestao['pasta_destino'])
                        nome_final = sugestao['nome_final']
                        
                        # Atualizar progresso
                        self.root.after(0, lambda i=i, total=len(self.sugestoes): self.progress.configure(value=i))
                        self.root.after(0, lambda p=f"[{i}/{len(self.sugestoes)}] Movendo: {arquivo_original.name}": 
                                       self.progress_var.set(p))
                        
                        # Criar pasta destino se não existir
                        pasta_destino.mkdir(parents=True, exist_ok=True)
                        
                        # Mover arquivo
                        destino_final = pasta_destino / nome_final
                        shutil.move(str(arquivo_original), str(destino_final))
                        
                        self.root.after(0, lambda orig=arquivo_original.name, dest=destino_final: 
                                       self.log(f"✅ Movido: {orig} -> {dest}"))
                    
                    self.root.after(0, lambda: messagebox.showinfo("Sucesso", "Mudanças aplicadas com sucesso!"))
                    self.root.after(0, lambda: self.log("🎉 Todas as mudanças foram aplicadas!"))
                    self.root.after(0, lambda: self.atualizar_status("Mudanças aplicadas"))
                    
                    # Limpar sugestões após aplicar
                    self.sugestoes = []
                    self.root.after(0, lambda: self.btn_aplicar.config(state='disabled'))
                    
                    # Limpar tabela de resultados
                    self.root.after(0, lambda: [self.tree.delete(item) for item in self.tree.get_children()])
                    
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro ao aplicar mudanças: {str(e)}"))
                    self.root.after(0, lambda: self.log(f"❌ Erro ao aplicar mudanças: {str(e)}"))
            
            # Executar em thread separada para não travar a interface
            threading.Thread(target=aplicar, daemon=True).start()
                
    def exportar_log(self):
        """Exporta o log para arquivo"""
        arquivo = filedialog.asksaveasfilename(
            title="Salvar Log",
            defaultextension=".txt",
            filetypes=[("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")]
        )
        
        if arquivo:
            try:
                with open(arquivo, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                    
                messagebox.showinfo("Sucesso", f"Log exportado para: {arquivo}")
                self.log(f"📤 Log exportado para: {arquivo}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar log: {str(e)}")
                
    def executar(self):
        """Executa a aplicação"""
        self.root.mainloop()

def main():
    app = OrganizadorGUI()
    app.executar()

if __name__ == "__main__":
    main()