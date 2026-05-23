# 🎮 The Floor Portugal — Engine Profissional

## 📌 Descrição do Projeto

**The Floor Portugal** é uma adaptação digital do famoso concurso televisivo *The Floor*, desenvolvida em **Python** no âmbito da unidade curricular de **Programação de Computadores II** da Escola de Engenharia da Universidade do Minho.

O objetivo principal do projeto consiste em recriar a dinâmica estratégica e competitiva do programa televisivo através de uma aplicação gráfica interativa, combinando:

- gestão de jogadores;
- sistema de duelos em tempo real;
- conquista territorial;
- persistência de dados;
- estatísticas avançadas;
- inteligência artificial para validação de respostas;
- interfaces gráficas modernas com Tkinter.

O jogo foi concebido com base no protocolo fornecido pelos docentes, respeitando os requisitos funcionais e técnicos definidos para o trabalho prático.

---

# 🧠 Conceito do Jogo

O jogo decorre num tabuleiro de **10x10**, representando um total de **100 participantes**, onde:

- cada célula representa um concorrente;
- cada jogador possui uma categoria temática;
- os jogadores desafiam territórios vizinhos;
- os vencedores conquistam territórios;
- os derrotados são eliminados;
- o último jogador ativo vence a competição.

Os duelos são realizados através de perguntas de cultura geral associadas à categoria do jogador desafiado.

---

# ⚙️ Funcionalidades Implementadas

## ✅ Sistema de Tabuleiro

- Tabuleiro dinâmico 10x10;
- Gestão automática de territórios;
- Conquista e herança de células;
- Verificação de vizinhança válida;
- Atualização visual em tempo real.

---

## ✅ Gestão de Jogadores

Cada jogador possui:

- ID único;
- categoria principal;
- cor personalizada;
- tempo individual;
- estatísticas completas;
- contagem de vitórias;
- histórico de respostas.

---

## ✅ Sistema de Duelos

O motor de duelos inclui:

- cronómetros independentes;
- perguntas aleatórias;
- sistema de skip;
- penalizações temporais;
- troca dinâmica de turnos;
- eliminação automática;
- fluxo de continuação estratégica.

---

## ✅ Inteligência Artificial (OLLAMA)

O projeto integra o modelo **Llama3** através da biblioteca **Ollama**, permitindo:

- validação inteligente de respostas;
- tolerância a erros ortográficos;
- reconhecimento de abreviações;
- aceitação de sinónimos;
- avaliação contextual das respostas.

---

## ✅ Persistência de Dados

O sistema suporta:

- gravação de jogos;
- carregamento de progresso;
- múltiplos slots de save;
- armazenamento em ficheiros JSON;
- recuperação segura de estados.

---

## ✅ Estatísticas e Relatórios

O jogo gera automaticamente:

- relatórios CSV;
- gráficos estatísticos;
- rankings territoriais;
- percentagens de sobrevivência;
- desempenho em duelos;
- histórico de respostas.

Os gráficos são produzidos através da biblioteca **Matplotlib**.

---

# 🖥️ Interface Gráfica

A aplicação utiliza **Tkinter** para fornecer:

- menus interativos;
- tabuleiro visual;
- janelas de duelo;
- painéis estatísticos;
- sistema de navegação;
- feedback visual em tempo real.

O design foi inspirado em interfaces modernas com:

- tema escuro;
- cores neon;
- organização modular;
- componentes reutilizáveis.

---

# 🧱 Estrutura Modular do Código

O projeto encontra-se organizado em múltiplos módulos lógicos:

| Módulo | Função |
|---|---|
| `StatsEngine` | Geração de gráficos e relatórios |
| `AIJudge` | Validação inteligente de respostas |
| `TheFloorGame` | Motor principal do jogo |
| Sistema JSON | Persistência de dados |
| Tkinter UI | Interface gráfica |

Esta abordagem promove:

- reutilização de código;
- manutenção simplificada;
- escalabilidade futura;
- separação de responsabilidades.

---

# 📂 Estrutura de Ficheiros

```bash
TheFloor/
│
├── perguntas.json
├── relatorio_jogadores.csv
├── saves_the_floor/
│   ├── save_slot_1.json
│   ├── save_slot_2.json
│   └── save_slot_3.json
│
├── relatorio_ranking_global.png
├── relatorio_respostas_top10.png
├── relatorio_sobrevivencia.png
├── relatorio_duelistas.png
│
└── main.py
```

---

# 🛠️ Tecnologias Utilizadas

## Linguagem

- Python 3

## Bibliotecas

- Tkinter
- Matplotlib
- PIL (Pillow)
- JSON
- CSV
- Threading
- Random
- Ollama

---

# 🚀 Como Executar

## 1️⃣ Instalar Dependências

```bash
pip install pillow matplotlib ollama
```

---

## 2️⃣ Instalar e Configurar Ollama

Instalar Ollama:

👉 https://ollama.com/

Executar o modelo:

```bash
ollama run llama3
```

---

## 3️⃣ Executar o Projeto

```bash
python main.py
```

---

# 📊 Funcionalidades Avançadas

O projeto inclui várias funcionalidades extra valorizadas no protocolo:

- sistema profissional de saves;
- gráficos automáticos;
- IA para arbitragem;
- arquitetura modular;
- tratamento de exceções;
- sistema de rankings;
- persistência robusta;
- interface gráfica avançada.

---

# 📚 Objetivos Académicos Cumpridos

Este projeto demonstra a aplicação prática dos seguintes conteúdos:

- algoritmia;
- programação modular;
- listas e dicionários;
- manipulação de ficheiros;
- interfaces gráficas;
- tratamento de exceções;
- estruturas de repetição;
- orientação lógica de sistemas;
- persistência de dados;
- geração de estatísticas;
- integração de APIs externas.

---

# 🔮 Melhorias Futuras

Possíveis evoluções do projeto:

- modo online multiplayer;
- integração com bases de dados SQL;
- sistema de contas;
- autenticação de jogadores;
- animações avançadas;
- efeitos sonoros;
- suporte para múltiplos idiomas;
- modo espectador;
- ranking global online.

---

# 👨‍💻 Autores

Projeto desenvolvido no âmbito da unidade curricular:

**Programação de Computadores II**  
Universidade do Minho — Escola de Engenharia

---

# 🏆 Conclusão

O projeto **The Floor Portugal — Engine Profissional** representa uma implementação completa e avançada do conceito do concurso televisivo “The Floor”, combinando programação em Python, inteligência artificial, persistência de dados, estatísticas e interfaces gráficas modernas.

Além de cumprir os requisitos definidos no protocolo do trabalho prático, o projeto demonstra capacidades avançadas de organização de software, modularização e desenvolvimento de aplicações interativas.

