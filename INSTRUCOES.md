# 📋 Instruções de Uso - Organizador de Arquivos com IA

## 🚀 Versão Avançada 2.0.0

Guia completo para usar o Organizador de Arquivos com IA em sua versão mais avançada.

### 🎯 Início Rápido

#### Windows
```bash
# Duplo clique no arquivo ou execute:
executar.bat
```

#### Linux/Mac
```bash
# Torne o script executável e execute:
chmod +x executar.sh
./executar.sh
```

#### Execução Direta
```bash
python main.py
```

### 🖥️ Interface da Aplicação

A nova interface é dividida em seções organizadas:

#### 📋 Painel de Configurações (Esquerda)
- **📁 Seleção de Pasta**: Escolha a pasta para organizar
- **🔧 Modo de Organização**: Quatro modos disponíveis
- **🔍 Filtros Avançados**: Configure filtros específicos
- **⚙️ Opções**: Backup automático e preview
- **🎯 Botões de Ação**: Analisar, visualizar, aplicar e cancelar

#### 📊 Painel de Resultados (Direita)
- **📋 Aba Resultados**: Tabela detalhada dos arquivos
- **📊 Aba Estatísticas**: Análise completa dos dados
- **📝 Aba Logs**: Histórico detalhado de operações
- **💾 Aba Backups**: Gestão de backups automáticos

### 🔧 Modos de Organização Avançados

#### 1. 📄 Por Tipo de Arquivo (Expandido)
Categorias mais detalhadas e personalizáveis:

- **📸 Imagens**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.svg`, `.webp`, `.tiff`, `.ico`, `.raw`
- **📄 Documentos**: `.pdf`, `.doc`, `.docx`, `.txt`, `.rtf`, `.odt`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.csv`
- **🎬 Vídeos**: `.mp4`, `.avi`, `.mkv`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.3gp`, `.ogv`
- **🎵 Áudio**: `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.wma`, `.m4a`, `.opus`, `.aiff`
- **📦 Compactados**: `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.bz2`, `.xz`, `.lzma`
- **⚙️ Executáveis**: `.exe`, `.msi`, `.deb`, `.rpm`, `.dmg`, `.app`, `.appx`
- **💻 Código**: `.py`, `.js`, `.html`, `.css`, `.java`, `.cpp`, `.c`, `.php`, `.go`, `.rs`
- **📁 Outros**: Arquivos não categorizados

#### 2. 📅 Por Data de Modificação (Melhorado)
- **Formato Flexível**: `YYYY-MM` ou `YYYY-MM-DD`
- **Períodos Personalizados**: Diário, mensal, anual
- **Filtros de Data**: Organize apenas arquivos de períodos específicos

#### 3. 🔤 Por Nome (A-Z) (Aprimorado)
- **Organização Inteligente**: Considera acentos e caracteres especiais
- **Subpastas Numéricas**: `0-9` para arquivos que começam com números
- **Caracteres Especiais**: Pasta `#` para símbolos

#### 4. ⚙️ Personalizado (NOVO!)
- **Regras Customizadas**: Crie suas próprias categorias
- **Múltiplos Critérios**: Combine tamanho, data, extensão
- **Salvamento de Regras**: Reutilize configurações

### 🔍 Sistema de Filtros Avançados

#### Filtro por Tamanho
- **Faixa Personalizável**: Defina tamanho mínimo e máximo
- **Unidades Flexíveis**: KB, MB, GB
- **Casos de Uso**: Separar arquivos grandes, encontrar duplicatas

#### Filtro por Data
- **Período Específico**: Data inicial e final
- **Datas Relativas**: Últimos 7 dias, último mês, etc.
- **Tipos de Data**: Criação, modificação, acesso

#### Filtro por Extensão
- **Lista Personalizada**: Especifique extensões exatas
- **Inclusão/Exclusão**: Inclua ou exclua tipos específicos
- **Wildcards**: Use padrões como `*.temp*`

#### Filtros Combinados
- **Múltiplos Filtros**: Use vários filtros simultaneamente
- **Lógica AND**: Todos os critérios devem ser atendidos
- **Preview de Filtros**: Veja quantos arquivos serão afetados

### 💾 Sistema de Backup Avançado

#### Backup Automático
- **Criação Automática**: Antes de cada operação
- **Metadados Completos**: Informações para restauração
- **Compressão Inteligente**: Economiza espaço em disco

#### Gestão de Backups
- **Lista Organizada**: Visualize todos os backups
- **Informações Detalhadas**: Data, tipo, quantidade de arquivos
- **Restauração Simples**: Um clique para desfazer
- **Limpeza Automática**: Remove backups antigos

#### Restauração
1. Acesse a aba **"💾 Backups"**
2. Selecione o backup desejado
3. Clique em **"↩️ Restaurar"**
4. Confirme a operação

### 📊 Sistema de Logs Detalhados

#### Tipos de Log
- **INFO**: Operações normais
- **WARNING**: Situações que requerem atenção
- **ERROR**: Erros que impediram operações
- **DEBUG**: Informações técnicas detalhadas

#### Funcionalidades
- **Timestamps Precisos**: Data e hora exatas
- **Exportação**: Salve logs em arquivos
- **Filtragem**: Visualize apenas tipos específicos
- **Limpeza**: Remova logs antigos

### 📋 Processo Detalhado Passo a Passo

#### Passo 1: Configuração Inicial
1. **Abra a aplicação** usando um dos métodos de execução
2. **Configure o tema** (claro/escuro) se desejar
3. **Verifique configurações** no menu de configurações

#### Passo 2: Seleção e Configuração
1. **Selecione a pasta** clicando em "📂 Selecionar"
2. **Escolha o modo** de organização
3. **Configure filtros** se necessário
4. **Ative opções** como backup automático

#### Passo 3: Análise Avançada
1. **Clique em "🔍 Analisar Arquivos"**
2. **Acompanhe o progresso** na barra inferior
3. **Monitore logs** na aba correspondente
4. **Aguarde conclusão** da análise

#### Passo 4: Revisão Detalhada
1. **Aba Resultados**: Revise a tabela completa
2. **Aba Estatísticas**: Analise distribuição e métricas
3. **Preview**: Use "👁️ Visualizar Preview" para ver estrutura
4. **Ajustes**: Modifique filtros se necessário

#### Passo 5: Aplicação Segura
1. **Confirme configurações** uma última vez
2. **Clique em "✅ Aplicar Organização"**
3. **Confirme no diálogo** de segurança
4. **Acompanhe progresso** em tempo real
5. **Verifique logs** para confirmar sucesso

### 🛡️ Recursos de Segurança

#### Validações Automáticas
- **Permissões de Arquivo**: Verifica acesso antes de mover
- **Espaço em Disco**: Confirma espaço suficiente
- **Integridade**: Valida arquivos antes e depois
- **Conflitos**: Detecta e resolve automaticamente

#### Proteções
- **Backup Obrigatório**: Criado automaticamente
- **Confirmação Dupla**: Diálogos de confirmação
- **Operação Reversível**: Sempre pode ser desfeita
- **Logs Completos**: Rastreamento total

### 🎨 Personalização da Interface

#### Temas
- **Tema Claro**: Interface clara e moderna
- **Tema Escuro**: Reduz cansaço visual
- **Personalização**: Cores e fontes ajustáveis

#### Layout
- **Redimensionável**: Ajuste painéis conforme necessário
- **Abas Organizadas**: Informações bem estruturadas
- **Responsivo**: Adapta-se ao tamanho da tela

### 📊 Interpretando Estatísticas Avançadas

#### Métricas Principais
- **Total de Arquivos**: Quantidade encontrada
- **Tamanho Total**: Espaço ocupado
- **Distribuição por Categoria**: Gráfico de categorias
- **Arquivos Maiores/Menores**: Extremos identificados

#### Análises
- **Tendências**: Padrões nos seus arquivos
- **Recomendações**: Sugestões de organização
- **Otimizações**: Oportunidades de melhoria

### 🛠️ Solução de Problemas Avançada

#### Problemas de Performance
**Sintoma**: Aplicação lenta com muitos arquivos
**Soluções**:
- Use filtros para reduzir escopo
- Processe em lotes menores
- Feche outros programas
- Use SSD se disponível

#### Problemas de Permissão
**Sintoma**: "Acesso negado" ou "Permissão insuficiente"
**Soluções**:
- Execute como administrador (Windows)
- Use sudo (Linux/Mac)
- Verifique propriedade dos arquivos
- Desative antivírus temporariamente

#### Problemas de Interface
**Sintoma**: Interface não responde ou trava
**Soluções**:
- Use botão "⏹️ Cancelar"
- Aguarde conclusão de operações
- Reinicie a aplicação
- Verifique logs para erros

#### Problemas de Backup
**Sintoma**: Backup falha ou não é criado
**Soluções**:
- Verifique espaço em disco
- Confirme permissões de escrita
- Limpe backups antigos
- Desative temporariamente se necessário

### 💡 Dicas e Truques Avançados

#### Organização Eficiente
- **Estratégia em Camadas**: Use múltiplos modos sequencialmente
- **Filtros Inteligentes**: Combine critérios para precisão
- **Backup Estratégico**: Mantenha backups importantes
- **Limpeza Regular**: Organize periodicamente

#### Automação
- **Regras Personalizadas**: Crie para casos específicos
- **Filtros Salvos**: Reutilize configurações comuns
- **Scripts**: Use linha de comando para automação

#### Performance
- **Lotes Pequenos**: Processe 500-1000 arquivos por vez
- **Filtros Primeiro**: Reduza escopo antes de analisar
- **SSD**: Use para melhor performance
- **RAM**: Mais memória = melhor performance

### 🔄 Casos de Uso Avançados

#### Organização de Projetos
1. **Filtro por Extensão**: Separe código, documentos, recursos
2. **Modo Personalizado**: Crie estrutura específica do projeto
3. **Backup**: Sempre antes de reestruturar
4. **Logs**: Documente mudanças para equipe

#### Limpeza de Downloads
1. **Filtro por Data**: Organize por período de download
2. **Filtro por Tamanho**: Identifique arquivos grandes
3. **Modo por Tipo**: Separe por categoria
4. **Limpeza**: Remove duplicatas e temporários

#### Gestão de Mídia
1. **Filtro por Extensão**: Separe fotos, vídeos, áudio
2. **Modo por Data**: Organize cronologicamente
3. **Backup**: Proteja arquivos importantes
4. **Estatísticas**: Analise uso de espaço

### 📤 Exportação e Relatórios

#### Exportação de Resultados
- **Formato JSON**: Dados estruturados para análise
- **Relatórios**: Informações resumidas
- **Logs Detalhados**: Histórico completo
- **Estatísticas**: Métricas em formato legível

#### Integração
- **Scripts Externos**: Use dados exportados
- **Análise**: Importe em planilhas
- **Auditoria**: Mantenha registros
- **Compliance**: Documente mudanças

### 🔮 Funcionalidades Futuras

#### Em Desenvolvimento
- **Interface Web**: Acesso via navegador
- **API REST**: Integração com outros sistemas
- **IA Avançada**: Categorização inteligente
- **Sincronização**: Entre múltiplos dispositivos

#### Planejadas
- **Mobile App**: Versão para smartphones
- **Cloud Integration**: Suporte a serviços de nuvem
- **Plugins**: Extensibilidade via plugins
- **Multi-idioma**: Suporte a vários idiomas

---

## 📞 Suporte e Comunidade

### Obter Ajuda
- **GitHub Issues**: Reporte bugs e solicite funcionalidades
- **Discussões**: Participe da comunidade
- **Email**: contato@organizador-ia.com
- **Wiki**: Documentação detalhada

### Contribuir
- **Código**: Contribua com melhorias
- **Documentação**: Ajude a melhorar guias
- **Testes**: Reporte bugs e teste funcionalidades
- **Traduções**: Ajude com localização

### Recursos Adicionais
- **Vídeo Tutoriais**: Canal no YouTube
- **Blog**: Dicas e atualizações
- **Newsletter**: Novidades por email
- **Fórum**: Comunidade de usuários

---

**Versão**: 2.0.0 - Organizador Avançado  
**Última atualização**: Dezembro 2024  
**Próxima atualização**: Janeiro 2025