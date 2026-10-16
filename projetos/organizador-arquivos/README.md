# 🗂️ Organizador de Arquivos com IA - Versão Avançada

Um organizador inteligente de arquivos com funcionalidades avançadas, interface moderna e sistema completo de backup e logs.

## ✨ Funcionalidades Principais

### 🎯 Organização Inteligente
- **Múltiplos Modos**: Por tipo, data, nome ou regras personalizadas
- **Análise Avançada**: Detecção automática de categorias e metadados
- **Preview de Organização**: Visualize antes de aplicar mudanças
- **Resolução de Conflitos**: Renomeação automática de arquivos duplicados

### 🔍 Filtros Avançados
- **Filtro por Tamanho**: Selecione arquivos por faixa de tamanho
- **Filtro por Data**: Organize por período de modificação
- **Filtro por Extensão**: Trabalhe com tipos específicos de arquivo
- **Filtros Combinados**: Use múltiplos critérios simultaneamente

### 💾 Sistema de Backup
- **Backup Automático**: Criação automática antes de cada operação
- **Restauração Completa**: Desfaça operações com um clique
- **Gestão de Backups**: Visualize, restaure ou exclua backups antigos
- **Limpeza Automática**: Remove backups antigos automaticamente

### 📊 Logs e Monitoramento
- **Logs Detalhados**: Registro completo de todas as operações
- **Exportação de Logs**: Salve logs em arquivos para análise
- **Estatísticas Avançadas**: Análise detalhada dos arquivos processados
- **Monitoramento em Tempo Real**: Acompanhe o progresso das operações

### 🎨 Interface Moderna
- **Design Responsivo**: Interface adaptável e intuitiva
- **Temas Claro/Escuro**: Personalize a aparência
- **Abas Organizadas**: Resultados, estatísticas, logs e backups
- **Drag & Drop**: Arraste pastas diretamente para a interface

## 🛠️ Tecnologias Utilizadas

- **Python 3.8+** - Linguagem principal
- **Tkinter** - Interface gráfica nativa
- **Threading** - Processamento assíncrono
- **JSON** - Configurações e dados
- **Pathlib** - Manipulação moderna de arquivos
- **Datetime** - Gestão de datas e timestamps

## 📦 Instalação

### Pré-requisitos
- Python 3.8 ou superior
- Sistema operacional: Windows, macOS ou Linux

### Instalação Rápida

1. **Clone o repositório:**
```bash
git clone https://github.com/seu-usuario/organizador-arquivos-ia.git
cd organizador-arquivos-ia
```

2. **Execute a aplicação:**
```bash
python main.py
```

*Nota: Este projeto usa apenas bibliotecas padrão do Python, não requer instalação de dependências externas.*

### Instalação com Funcionalidades Opcionais

Para funcionalidades avançadas (análise de metadados, interface web, etc.):

```bash
pip install -r requirements-optional.txt
```

## 🚀 Como Usar

### 1. Iniciar a Aplicação
```bash
python main.py
```

### 2. Selecionar Pasta
- Clique em "📂 Selecionar" para escolher a pasta a organizar
- Ou arraste a pasta diretamente para a interface

### 3. Configurar Organização
- **Modo**: Escolha como organizar (tipo, data, nome, personalizado)
- **Filtros**: Configure filtros avançados se necessário
- **Opções**: Ative backup automático e preview

### 4. Analisar e Organizar
- Clique em "🔍 Analisar Arquivos" para ver o que será feito
- Revise os resultados na aba "📋 Resultados"
- Visualize estatísticas na aba "📊 Estatísticas"
- Clique em "✅ Aplicar Organização" para executar

### 5. Monitorar e Gerenciar
- Acompanhe logs na aba "📝 Logs"
- Gerencie backups na aba "💾 Backups"
- Exporte resultados e logs conforme necessário

## 📋 Modos de Organização

### 📄 Por Tipo de Arquivo
Organiza arquivos em categorias:
- **Imagens**: jpg, png, gif, bmp, svg, webp, etc.
- **Documentos**: pdf, doc, docx, txt, rtf, odt, etc.
- **Vídeos**: mp4, avi, mkv, mov, wmv, flv, etc.
- **Áudio**: mp3, wav, flac, aac, ogg, m4a, etc.
- **Compactados**: zip, rar, 7z, tar, gz, etc.
- **Executáveis**: exe, msi, deb, rpm, dmg, etc.
- **Código**: py, js, html, css, java, cpp, etc.
- **Outros**: Arquivos não categorizados

### 📅 Por Data de Modificação
Cria pastas baseadas na data:
- Formato: `YYYY-MM` (ex: 2024-01, 2024-02)
- Organização cronológica automática
- Fácil localização por período

### 🔤 Por Nome (A-Z)
Organização alfabética:
- Pastas A, B, C... Z
- Pasta "#" para arquivos que começam com números/símbolos
- Ordenação automática

### ⚙️ Personalizado
Regras customizadas:
- Defina suas próprias categorias
- Crie regras baseadas em múltiplos critérios
- Salve e reutilize configurações

## 🔧 Configurações Avançadas

### Arquivo de Configuração
O sistema usa `config/user_settings.json` para:
- Preferências de interface
- Configurações de backup
- Filtros personalizados
- Temas e aparência

### Categorias Personalizadas
Personalize categorias editando as configurações:
```json
{
  "custom_categories": {
    "Minha Categoria": {
      "extensions": [".ext1", ".ext2"],
      "description": "Descrição da categoria"
    }
  }
}
```

## 📊 Estrutura do Projeto

```
organizador-arquivos-ia/
├── main.py                     # Ponto de entrada principal
├── requirements.txt            # Dependências básicas
├── README.md                   # Documentação principal
├── INSTRUCOES.md              # Instruções detalhadas
│
├── src/                       # Código fonte principal
│   ├── __init__.py           # Inicialização do pacote
│   ├── core/                 # Lógica principal
│   │   ├── organizer.py      # Organizador avançado
│   │   └── filters.py        # Sistema de filtros
│   ├── gui/                  # Interface gráfica
│   │   └── main_window.py    # Janela principal
│   └── utils/                # Utilitários
│       ├── logger.py         # Sistema de logs
│       ├── backup.py         # Sistema de backup
│       └── validator.py      # Validações
│
├── config/                   # Configurações
│   └── settings.py          # Configurações centralizadas
│
├── logs/                     # Logs da aplicação
├── backups/                  # Backups automáticos
└── temp/                     # Arquivos temporários
```

## 🛡️ Segurança e Confiabilidade

### Sistema de Backup
- **Backup Automático**: Criado antes de cada operação
- **Metadados Completos**: Informações detalhadas para restauração
- **Verificação de Integridade**: Validação de backups
- **Restauração Segura**: Processo reversível e confiável

### Validações
- **Permissões de Arquivo**: Verifica acesso antes de mover
- **Espaço em Disco**: Confirma espaço suficiente
- **Conflitos de Nome**: Resolução automática
- **Integridade de Dados**: Verificação de corrupção

### Logs Detalhados
- **Operações Completas**: Registro de todas as ações
- **Timestamps Precisos**: Rastreamento temporal
- **Níveis de Log**: Info, Warning, Error, Debug
- **Exportação Segura**: Backup de logs importantes

## 🎯 Casos de Uso

### 📁 Organização de Downloads
- Categorize automaticamente arquivos baixados
- Separe por tipo e data
- Mantenha pasta Downloads sempre organizada

### 🖼️ Gestão de Fotos
- Organize fotos por data
- Separe por eventos ou categorias
- Backup automático antes de mover

### 📄 Documentos de Trabalho
- Categorize por tipo de documento
- Organize por projeto ou data
- Mantenha histórico de mudanças

### 💻 Projetos de Código
- Organize arquivos de código por linguagem
- Separe recursos e documentação
- Backup antes de reestruturação

## 🤝 Contribuição

Contribuições são bem-vindas! Para contribuir:

1. **Fork** o projeto
2. **Crie** uma branch para sua feature:
   ```bash
   git checkout -b feature/nova-funcionalidade
   ```
3. **Commit** suas mudanças:
   ```bash
   git commit -m 'Adiciona nova funcionalidade'
   ```
4. **Push** para a branch:
   ```bash
   git push origin feature/nova-funcionalidade
   ```
5. **Abra** um Pull Request

### Diretrizes de Contribuição
- Mantenha o código limpo e documentado
- Adicione testes para novas funcionalidades
- Siga as convenções de código existentes
- Atualize a documentação quando necessário

## 📄 Licença

Este projeto está sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.

## 🆘 Suporte

### Problemas Comuns

**Erro de Permissão:**
- Execute como administrador (Windows) ou use sudo (Linux/Mac)
- Verifique permissões da pasta de destino

**Interface não Abre:**
- Verifique se Python 3.8+ está instalado
- Confirme que tkinter está disponível

**Backup Falha:**
- Verifique espaço em disco
- Confirme permissões de escrita

### Obter Ajuda
- **Issues**: Reporte bugs no GitHub
- **Discussões**: Participe das discussões da comunidade
- **Email**: contato@organizador-ia.com

## 🎉 Agradecimentos

- **Comunidade Python** pelas excelentes bibliotecas
- **Contribuidores** que ajudaram a melhorar o projeto
- **Usuários** que forneceram feedback valioso
- **Testadores** que ajudaram a encontrar e corrigir bugs

## 🔮 Roadmap

### Próximas Funcionalidades
- [ ] Interface web moderna
- [ ] Integração com serviços de nuvem
- [ ] Análise de metadados avançada
- [ ] Agendamento de tarefas
- [ ] API REST para automação
- [ ] Plugin para exploradores de arquivo
- [ ] Suporte a regras baseadas em IA
- [ ] Interface mobile

### Melhorias Planejadas
- [ ] Performance otimizada para grandes volumes
- [ ] Suporte a mais formatos de arquivo
- [ ] Temas personalizáveis
- [ ] Localização em múltiplos idiomas
- [ ] Integração com antivírus
- [ ] Análise de duplicatas
- [ ] Compressão inteligente
- [ ] Sincronização entre dispositivos

---

⭐ **Se este projeto foi útil para você, considere dar uma estrela no GitHub!**

🚀 **Versão Atual**: 2.0.0 - Organizador Avançado  
📅 **Última Atualização**: Dezembro 2024  
👥 **Contribuidores**: [Lista de Contribuidores](CONTRIBUTORS.md)