import tkinter as tk
from tkinter import messagebox, ttk
import random
import time
import json
import os
import csv
import threading
import re
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from PIL import Image, ImageTk

import ollama

# =================================================================
# CONFIGURAÇÕES DO TABULEIRO E SISTEMA
# =================================================================
GRID_SIZE = 10  
OLLAMA_MODEL = "llama3" 
SAVE_DIR = "saves_the_floor"

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# =================================================================
# MÓDULO 1: GERADOR DE ESTATÍSTICAS E GRÁFICOS (STATS ENGINE)
# =================================================================
class StatsEngine:
    @staticmethod
    def exportar_estatisticas_csv(players):
        pasta_do_script = os.path.dirname(os.path.abspath(__file__))
        caminho_csv = os.path.join(pasta_do_script, 'relatorio_jogadores.csv')
        
        headers = ["ID_Jogador", "Categoria_Inicial", "Estado", "Territorio_Atual_m2", "Tamanho_Maximo_Atingido", "Respostas_Certas", "Respostas_Erradas_Com_Skips", "Duelos_Vencidos"]
        try:
            with open(caminho_csv, mode='w', encoding='utf-8-sig', newline='') as f:
                f.write("sep=;\n")
                writer = csv.writer(f, delimiter=';')
                writer.writerow(headers)
                for p in players:
                    estado = "ATIVO" if p["active"] else "ELIMINADO"
                    writer.writerow([
                        p["id"], p["main_cat"], estado, p["cells"], 
                        p["max_cells"], p["certas"], p["erradas"], p["vitorias_duelo"]
                    ])
        except Exception as e:
            print(f"Erro ao exportar CSV: {e}")

    @staticmethod
    def atualizar_e_salvar_graficos(players):
        pasta_do_script = os.path.dirname(os.path.abspath(__file__))
        jogadores_ranqueados = sorted(players, key=lambda x: x["cells"], reverse=True)
        top_10 = jogadores_ranqueados[:10]
        
        if not top_10: 
            return

        plt.style.use('dark_background')

        # --- GRÁFICO 1: TERRITÓRIOS ---
        labels_t = [f"J{p['id']}" for p in top_10]
        territorios = [p["cells"] for p in top_10]
        cores_t = [p["color"] for p in top_10]

        plt.figure(1, figsize=(7, 4.5))
        plt.clf() 
        plt.bar(labels_t, territorios, color=cores_t, edgecolor="white", alpha=0.8)
        plt.title('Top 10 Maiores Impérios Ativos (m²)', fontsize=12, fontweight='bold', color='#00F2FF')
        plt.ylabel('Células Conquistadas')
        plt.tick_params(axis='both', which='major', labelsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(pasta_do_script, 'relatorio_ranking_global.png'), dpi=120)
        plt.close(1)

        # --- GRÁFICO 2: PERFORMANCE ---
        ids_jogadores = [f"J{p['id']}" for p in top_10]
        certas = [p["certas"] for p in top_10]
        erradas = [p["erradas"] for p in top_10]
        
        x = range(len(ids_jogadores))
        width = 0.35
        
        plt.figure(2, figsize=(7, 4.5))
        plt.clf()
        plt.bar([i - width/2 for i in x], certas, width, label='Certas', color='#00FF66') 
        plt.bar([i + width/2 for i in x], erradas, width, label='Erradas', color='#FF3333') 
        plt.title('Histórico de Respostas (Top 10)', fontsize=12, fontweight='bold', color='#00F2FF')
        plt.xticks(x, ids_jogadores, fontsize=9)
        plt.ylabel('Quantidade')
        plt.legend(loc='upper right', fontsize=9)
        plt.grid(axis='y', linestyle='--', alpha=0.2)
        plt.tight_layout()
        plt.savefig(os.path.join(pasta_do_script, 'relatorio_respostas_top10.png'), dpi=120)
        plt.close(2)

        # --- GRÁFICO 3: DOMINAÇÃO TOTAL ---
        ativos = sum(1 for p in players if p["active"])
        eliminados = len(players) - ativos
        
        plt.figure(3, figsize=(7, 4.5))
        plt.clf()
        plt.pie([ativos, eliminados], labels=['Ativos', 'Eliminados'], colors=['#00F2FF', '#333333'], 
                autopct='%1.1f%%', startangle=90, textprops={'fontsize': 9})
        plt.title('Percentagem de Sobrevivência', fontsize=12, fontweight='bold', color='#00F2FF')
        plt.tight_layout()
        plt.savefig(os.path.join(pasta_do_script, 'relatorio_sobrevivencia.png'), dpi=120)
        plt.close(3)

        # --- GRÁFICO 4: RECORDISTAS DE DUELOS ---
        top_duelistas = sorted(players, key=lambda x: x["vitorias_duelo"], reverse=True)[:5]
        nomes_d = [f"J{p['id']} ({p['main_cat'][:8]})" for p in top_duelistas]
        vitorias = [p["vitorias_duelo"] for p in top_duelistas]

        plt.figure(4, figsize=(7, 4.5))
        plt.clf()
        plt.barh(nomes_d, vitorias, color='#FFCC00', edgecolor="orange")
        plt.gca().invert_yaxis()
        plt.title('Top 5 Reis do Palco (Mais Vitórias)', fontsize=12, fontweight='bold', color='#00F2FF')
        plt.xlabel('Vitórias em Duelo')
        plt.tick_params(axis='both', which='major', labelsize=9)
        plt.gca().xaxis.get_major_locator().set_params(integer=True)
        plt.tight_layout()
        plt.savefig(os.path.join(pasta_do_script, 'relatorio_duelistas.png'), dpi=120)
        plt.close(4)


# =================================================================
# MÓDULO 2: ARBITRAGEM INTELIGENTE (AI JUDGE)
# =================================================================
class AIJudge:
    @staticmethod
    def verificar_resposta(pergunta, resposta_esperada, resposta_utilizador):
        resp_utilizador_clean = resposta_utilizador.lower().strip()
        resp_esperada_clean = resposta_esperada.lower().strip()
        
        if not resp_utilizador_clean:
            return False

        if resp_utilizador_clean in resp_esperada_clean or resp_esperada_clean in resp_utilizador_clean:
            if len(resp_utilizador_clean) > 2:
                return True

        prompt = f"""
        Atuas como um juiz tolerante e inteligente de um jogo de trivia em Português.
        Pergunta feita: "{pergunta}"
        Gabarito oficial: "{resposta_esperada}"
        Resposta do jogador: "{resposta_utilizador}"

        REGRAS DE VALIDAÇÃO:
        1. Sê tolerante! Se o jogador simplificou a resposta, deves aceitar como CORRETO (Ex: Gabarito é 'AC Milan' e o jogador disse 'Milan'; Gabarito é 'Vasco da Gama' e o jogador disse 'Vasco').
        2. Aceita sinónimos óbvios, abreviações populares, omissão de artigos (o, a, os, as) ou pequenos erros de digitação.
        3. Só deves retirar a razão se a resposta for factualmente diferente ou errada.
        
        Deves responder OBRIGATORIAMENTE no formato JSON abaixo:
        {{
            "resultado": "CORRETO" ou "INCORRETO"
        }}
        """
        try:
            response = ollama.chat(
                model=OLLAMA_MODEL, 
                messages=[{'role': 'user', 'content': prompt}],
                format='json'
            )
            content = response['message']['content'].strip()
            
            # Sanitização extra: Remove marcações Markdown comuns vindas de LLMs locais
            content = re.sub(r'^```json\s*', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\s*```$', '', content)
            
            dados_resposta = json.loads(content)
            status = dados_resposta.get("resultado", "INCORRETO").strip().upper()
            return "CORRETO" in status
        except Exception as e:
            print(f"Erro na IA: {e}. Usando verificação por contenção.")
            return resp_utilizador_clean in resp_esperada_clean or resp_esperada_clean in resp_utilizador_clean


# =================================================================
# MÓDULO 3: GESTÃO DE FICHEIROS E BASE DE DADOS
# =================================================================
def carregar_base_dados():
    file_path = "perguntas.json"
    if not os.path.exists(file_path):
        exemplo = {
            "Culinária Tradicional Portuguesa": [
                {"pergunta": "Qual o ingrediente principal do Bacalhau à Brás?", "resposta": "Bacalhau"},
                {"pergunta": "Que doce conventual é típico de Belém?", "resposta": "Pastel de Belém"}
            ],
            "História de Portugal e Descobrimentos": [
                {"pergunta": "Quem chegou à Índia em 1498?", "resposta": "Vasco da Gama"},
                {"pergunta": "Em que ano ocorreu a Revolution dos Cravos?", "resposta": "1974"}
            ],
            "Geografia do Continent Europeu": [
                {"pergunta": "Qual a capital da França?", "resposta": "Paris"},
                {"pergunta": "Qual o maior rio que passa em Lisboa?", "resposta": "Tejo"}
            ]
        }
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(exemplo, f, indent=4, ensure_ascii=False)
    
    with open(file_path, "r", encoding='utf-8') as f:
        dados_base = json.load(f)
    
    pilhas = {cat: list(itens) for cat, itens in dados_base.items()}
    for cat in pilhas:
        random.shuffle(pilhas[cat])
    return dados_base, pilhas

def puxar_pergunta(dados_base, pilhas, categoria):
    if categoria not in pilhas or not pilhas[categoria]:
        pilhas[categoria] = list(dados_base.get(categoria, [{"pergunta": "Sem perguntas", "resposta": "N/A"}]))
        random.shuffle(pilhas[categoria])
    return pilhas[categoria].pop()


# =================================================================
# ESTILOS E PALETA VISUAL
# =================================================================
class Theme:
    BG = "#05070A"; CARD = "#10141D"; ACCENT = "#00F2FF"; TEXT = "#E1E7EF"; WARN = "#FFCC00"
    CLOCK = ("Courier New", 45, "bold")
    BOARD_FONT = ("Segoe UI", 8, "bold") 


# =================================================================
# CONTROLADOR PRINCIPAL DO JOGO
# =================================================================
class TheFloorGame:
    def __init__(self, root):
        self.root = root
        self.root.title("THE FLOOR PORTUGAL - ENGINE PROFISSIONAL")
        self.root.state('zoomed') 
        self.root.configure(bg=Theme.BG)
        
        self.dados_base, self.pilhas = carregar_base_dados()
        self.all_cats = list(self.dados_base.keys())
        self.grid_widgets = {}
        self.ranking_widgets = [] # Cache de controle para evitar leak de memória
        self.loop_id = None  
        self.current_save_slot = None
        
        self.ia_checking = False
        self.duel_active = False
        
        self.main_menu()

    def main_menu(self):
        for w in self.root.winfo_children(): w.destroy()
        
        frame = tk.Frame(self.root, bg=Theme.BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(frame, text="THE FLOOR", font=("Impact", 90), fg=Theme.ACCENT, bg=Theme.BG).pack()
        tk.Label(frame, text="SISTEMA DE GESTÃO E CAPTURAS PRO", font=("Segoe UI", 14, "italic"), fg=Theme.TEXT, bg=Theme.BG).pack(pady=5)
        
        btn_opts = {"font": ("Segoe UI", 13, "bold"), "bg": Theme.CARD, "fg": "white", "activebackground": Theme.ACCENT, "cursor": "hand2", "width": 30, "pady": 10}
        
        tk.Button(frame, text="NOVA COMPETIÇÃO", command=self.setup_game, **btn_opts).pack(pady=8)
        tk.Button(frame, text="CARREGAR / CONTINUAR JOGO", command=self.menu_saves, **btn_opts).pack(pady=8)
        tk.Button(frame, text="ESTATÍSTICAS E RELATÓRIOS", command=self.menu_estatisticas, **btn_opts).pack(pady=8)
        tk.Button(frame, text="SAIR DO JOGO", command=self.root.quit, **btn_opts).pack(pady=8)

    def menu_saves(self):
        for w in self.root.winfo_children(): w.destroy()
        
        frame = tk.Frame(self.root, bg=Theme.BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(frame, text="SLOTS DE GRAVAÇÃO", font=("Impact", 45), fg=Theme.ACCENT, bg=Theme.BG).pack(pady=20)
        
        for slot in range(1, 4):
            slot_frame = tk.Frame(frame, bg=Theme.CARD, padx=15, pady=10, highlightbackground="#222", highlightthickness=1)
            slot_frame.pack(fill="x", pady=10)
            
            path = os.path.join(SAVE_DIR, f"save_slot_{slot}.json")
            existe = os.path.exists(path)
            
            if existe:
                meta = {}
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        meta = json.load(f).get("metadata", {})
                    txt = f"Slot {slot}: {meta.get('jogadores_ativos', 0)} Jogadores Ativos\nSalvo em: {meta.get('data_hora', 'N/A')}"
                    fg_color = "#FFFFFF"
                except Exception:
                    txt = f"Slot {slot}: [ERRO - FICHEIRO CORROMPIDO]"
                    fg_color = "#FF3333"
                    existe = False 
            else:
                txt = f"Slot {slot}: [VAZIO / DISPONÍVEL]"
                fg_color = "#777777"
                
            tk.Label(slot_frame, text=txt, font=("Segoe UI", 11), fg=fg_color, bg=Theme.CARD, width=40, anchor="w").pack(side="left", padx=10)
            
            if existe:
                tk.Button(slot_frame, text="CONTINUAR", bg="#00FF66", fg="black", font=("Segoe UI", 10, "bold"), command=lambda s=slot: self.carregar_jogo(s)).pack(side="left", padx=5)
                tk.Button(slot_frame, text="APAGAR", bg="#FF3333", fg="white", font=("Segoe UI", 10, "bold"), command=lambda s=slot: self.apagar_save(s)).pack(side="left", padx=5)
            else:
                btn_load = tk.Button(slot_frame, text="VAZIO", state="disabled", font=("Segoe UI", 10))
                btn_load.pack(side="left", padx=5)
                if not existe and os.path.exists(path): 
                     tk.Button(slot_frame, text="REPARAR (APAGAR)", bg="#FF3333", fg="white", font=("Segoe UI", 10, "bold"), command=lambda s=slot: self.apagar_save(s)).pack(side="left", padx=5)
                
        tk.Button(frame, text="VOLTAR AO MENU", font=("Segoe UI", 11, "bold"), bg=Theme.WARN, fg="black", command=self.main_menu, padx=20, pady=5).pack(pady=30)

    def menu_estatisticas(self):
        for w in self.root.winfo_children(): w.destroy()
        
        top_bar = tk.Frame(self.root, bg=Theme.CARD, height=70)
        top_bar.pack(side="top", fill="x")
        top_bar.pack_propagate(False)
        
        tk.Label(top_bar, text="CENTRAL DE ANÁLISE EM REAL-TIME", font=("Impact", 28), fg=Theme.ACCENT, bg=Theme.CARD).pack(side="left", padx=20, pady=10)
        tk.Button(top_bar, text="VOLTAR AO MENU PRINCIPAL", font=("Segoe UI", 11, "bold"), bg=Theme.WARN, fg="black", 
                  command=self.main_menu, padx=20, cursor="hand2").pack(side="right", padx=20, pady=12)

        paned_window = tk.PanedWindow(self.root, orient="horizontal", bg=Theme.BG, bd=0, sashwidth=6)
        paned_window.pack(fill="both", expand=True, padx=15, pady=15)

        # PAINEL ESQUERDO: TABELA DO FICHEIRO CSV
        left_frame = tk.Frame(paned_window, bg=Theme.CARD, padx=10, pady=10)
        paned_window.add(left_frame, width=540)
        
        tk.Label(left_frame, text="DADOS NATIVOS DA GRAVAÇÃO (.CSV)", font=("Segoe UI", 12, "bold"), fg=Theme.ACCENT, bg=Theme.CARD).pack(anchor="w", pady=(0, 10))
        
        path_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'relatorio_jogadores.csv')
        
        colunas = ("id", "cat", "estado", "cells", "max_cells", "certas", "erradas", "vitorias")
        tree = ttk.Treeview(left_frame, columns=colunas, show="headings", selectmode="browse")
        
        tree.heading("id", text="ID")
        tree.heading("cat", text="Categoria")
        tree.heading("estado", text="Estado")
        tree.heading("cells", text="m²")
        tree.heading("max_cells", text="Max m²")
        tree.heading("certas", text="Certas")
        tree.heading("erradas", text="Erradas")
        tree.heading("vitorias", text="Vitórias")
        
        tree.column("id", width=35, anchor="center")
        tree.column("cat", width=140, anchor="w")
        tree.column("estado", width=75, anchor="center")
        tree.column("cells", width=40, anchor="center")
        tree.column("max_cells", width=55, anchor="center")
        tree.column("certas", width=50, anchor="center")
        tree.column("erradas", width=55, anchor="center")
        tree.column("vitorias", width=55, anchor="center")
        
        scroll_y_tree = ttk.Scrollbar(left_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll_y_tree.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scroll_y_tree.pack(side="right", fill="y")
        
        if os.path.exists(path_csv):
            try:
                with open(path_csv, mode='r', encoding='utf-8-sig') as f:
                    linhas = list(csv.reader(f, delimiter=';'))
                    if linhas and "sep=" in linhas[0][0]:
                        linhas.pop(0)
                    if linhas:
                        linhas.pop(0)
                    
                    for row in linhas:
                        if row:
                            tags = ("eliminado",) if row[2] == "ELIMINADO" else ("ativo",)
                            tree.insert("", "end", values=row, tags=tags)
                
                tree.tag_configure("ativo", foreground="#E1E7EF")
                tree.tag_configure("eliminado", foreground="#555964")
            except Exception as csv_err:
                print(f"Erro ao ler CSV: {csv_err}")
        else:
            tree.insert("", "end", values=("N/A", "Nenhum jogo registado ainda", "-", "-", "-", "-", "-", "-"))

        # PAINEL DIREITO: SCROLL 2D
        right_container = tk.Frame(paned_window, bg=Theme.CARD)
        paned_window.add(right_container, width=740)
        
        canvas_area = tk.Frame(right_container, bg=Theme.BG)
        canvas_area.grid(row=0, column=0, sticky="nsew")
        
        canvas_graficos = tk.Canvas(canvas_area, bg=Theme.BG, highlightthickness=0)
        
        scroll_y_graficos = ttk.Scrollbar(right_container, orient="vertical", command=canvas_graficos.yview)
        scroll_x_graficos = ttk.Scrollbar(right_container, orient="horizontal", command=canvas_graficos.xview)
        
        canvas_graficos.configure(yscrollcommand=scroll_y_graficos.set, xscrollcommand=scroll_x_graficos.set)
        
        scrollable_frame_graficos = tk.Frame(canvas_graficos, bg=Theme.BG)
        
        scrollable_frame_graficos.bind(
            "<Configure>",
            lambda e: canvas_graficos.configure(scrollregion=canvas_graficos.bbox("all"))
        )
        
        canvas_graficos.create_window((0, 0), window=scrollable_frame_graficos, anchor="nw")
        
        # Suporte a Scroll do Rato na Central de Estatísticas
        def _on_mousewheel_stats(event):
            canvas_graficos.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas_graficos.bind_all("<MouseWheel>", _on_mousewheel_stats)
        
        right_container.grid_rowconfigure(0, weight=1)
        right_container.grid_columnconfigure(0, weight=1)
        
        canvas_graficos.pack(side="top", fill="both", expand=True)
        scroll_y_graficos.grid(row=0, column=1, sticky="ns")
        scroll_x_graficos.grid(row=1, column=0, sticky="ew")
        
        pasta_do_script = os.path.dirname(os.path.abspath(__file__))
        lista_caminhos = [
            (os.path.join(pasta_do_script, 'relatorio_ranking_global.png'), 0, 0, "1. Domínio Territorial (Top 10)"), 
            (os.path.join(pasta_do_script, 'relatorio_respostas_top10.png'), 0, 1, "2. Eficiência de Respostas"),
            (os.path.join(pasta_do_script, 'relatorio_sobrevivencia.png'), 1, 0, "3. Estado de Sobrevivência"), 
            (os.path.join(pasta_do_script, 'relatorio_duelistas.png'), 1, 1, "4. Desempenho em Duelos")
        ]
        
        self.img_refs = []  
        
        grid_graficos = tk.Frame(scrollable_frame_graficos, bg=Theme.BG)
        grid_graficos.pack(fill="both", expand=True, padx=15, pady=15)
        
        for caminho, row, col, tit_grafico in lista_caminhos:
            box = tk.Frame(grid_graficos, bg=Theme.CARD, bd=1, highlightbackground="#222", highlightthickness=1, padx=8, pady=8)
            box.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
            
            if os.path.exists(caminho):
                try:
                    raw_img = Image.open(caminho)
                    tk_bitmap = ImageTk.PhotoImage(raw_img)
                    lbl_imagem = tk.Label(box, image=tk_bitmap, bg=Theme.CARD)
                    lbl_imagem.pack()
                    self.img_refs.append(tk_bitmap)
                except Exception as img_err:
                    tk.Label(box, text=f"[Erro ao renderizar gráfico: {img_err}]", fg="#FF3333", bg=Theme.CARD).pack(pady=50)
            else:
                tk.Label(box, text=f"{tit_grafico}\n\n[Gráfico pendente]\nInicie uma competição ou jogue uma ronda para gerar os dados.", 
                         font=("Segoe UI", 11, "italic"), fg="#777777", bg=Theme.CARD, width=42, height=14).pack(pady=30)

    # =================================================================
    # PERSISTÊNCIA DE DADOS (JSON INTEGRADO)
    # =================================================================
    def salvar_jogo_caixa_dialogo(self):
        d_save = tk.Toplevel(self.root)
        d_save.title("GRAVAR JOGO")
        d_save.geometry("400x300")
        d_save.configure(bg=Theme.CARD)
        d_save.grab_set()
        
        tk.Label(d_save, text="Escolha o Slot para Salvar:", font=("Segoe UI", 12, "bold"), fg=Theme.ACCENT, bg=Theme.CARD).pack(pady=15)
        
        for slot in range(1, 4):
            path = os.path.join(SAVE_DIR, f"save_slot_{slot}.json")
            status = "[Utilizado]" if os.path.exists(path) else "[Livre]"
            tk.Button(d_save, text=f"Slot {slot} {status}", font=("Segoe UI", 11), bg=Theme.BG, fg="white", width=25,
                      command=lambda s=slot: [self.executar_salvamento(s), d_save.destroy()]).pack(pady=8)

    def executar_salvamento(self, slot):
        path = os.path.join(SAVE_DIR, f"save_slot_{slot}.json")
        try:
            board_data = []
            for r in range(GRID_SIZE):
                row_data = []
                for c in range(GRID_SIZE):
                    row_data.append({
                        "owner_id": self.board[r][c]["owner"]["id"],
                        "cat": self.board[r][c]["cat"]
                    })
                board_data.append(row_data)
                
            dados_totais = {
                "metadata": {
                    "data_hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "jogadores_ativos": sum(1 for p in self.players if p["active"])
                },
                "current_player_id": self.current_player_id,
                "players": self.players,
                "board": board_data
            }
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(dados_totais, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Sucesso", f"O progresso da competição foi guardado no Slot {slot}!")
            self.update_ui()
        except Exception as save_err:
            messagebox.showerror("Erro de Escrita", f"Não foi possível gravar o jogo no disco:\n{save_err}")

    def carregar_jogo(self, slot):
        path = os.path.join(SAVE_DIR, f"save_slot_{slot}.json")
        if not os.path.exists(path): 
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                dados = json.load(f)
                
            self.current_player_id = dados["current_player_id"]
            self.players = dados["players"]
            
            mapa_players = {p["id"]: p for p in self.players}
            
            self.board = []
            for r in range(GRID_SIZE):
                row = []
                for c in range(GRID_SIZE):
                    celula_dados = dados["board"][r][c]
                    p_id = celula_dados["owner_id"]
                    row.append({
                        "owner": mapa_players[p_id],
                        "cat": celula_dados["cat"]
                    })
                self.board.append(row)
                
            messagebox.showinfo("Sucesso", f"Slot {slot} carregado com sucesso!")
            self.render_arena()
        except Exception as f_err:
            messagebox.showerror("Gravação Corrompida", f"Erro crítico ao carregar dados:\n{f_err}")

    def apagar_save(self, slot):
        if messagebox.askyesno("Confirmar", f"Tem a certeza de que deseja eliminar definitivamente o ficheiro do Slot {slot}?"):
            path = os.path.join(SAVE_DIR, f"save_slot_{slot}.json")
            try:
                if os.path.exists(path):
                    os.remove(path)
                self.menu_saves()
            except Exception as delete_err:
                messagebox.showerror("Erro de Sistema", f"Impossível remover ficheiro do disco: {delete_err}")


    # =================================================================
    # SISTEMA DE CONTROLO DE FLUXO DE PARTIDA
    # =================================================================
    def setup_game(self):
        total_celulas = GRID_SIZE * GRID_SIZE
        pool_cats = (self.all_cats * (total_celulas // len(self.all_cats) + 1))[:total_celulas]
        random.shuffle(pool_cats)
        
        self.players = []
        self.board = []
        idx = 1
        for r in range(GRID_SIZE):
            row = []
            for c in range(GRID_SIZE):
                color = f'#{random.randint(40,210):02x}{random.randint(40,210):02x}{random.randint(40,210):02x}'
                cat_nome = pool_cats[idx-1]
                p = {
                    "id": idx, "main_cat": cat_nome, "color": color, 
                    "time": 45.0, "active": True, "cells": 1,
                    "max_cells": 1, "certas": 0, "erradas": 0, "vitorias_duelo": 0
                }
                self.players.append(p)
                row.append({"owner": p, "cat": cat_nome})
                idx += 1
            self.board.append(row)
        
        StatsEngine.atualizar_e_salvar_graficos(self.players)
        StatsEngine.exportar_estatisticas_csv(self.players)
        self.pick_random_attacker()

    def get_player_by_id(self, p_id):
        for p in self.players:
            if p["id"] == p_id:
                return p
        return None

    def verificar_fim_de_jogo(self):
        active_ps = [p for p in self.players if p["active"]]
        if len(active_ps) <= 1:
            winner = active_ps[0] if active_ps else None
            messagebox.showinfo("FIM DA COMPETIÇÃO", f"O GRANDE VENCEDOR QUE CONQUISTOU TODO O TABULEIRO É O JOGADOR {winner['id']}!")
            self.main_menu()
            return True
        return False

    def pick_random_attacker(self):
        if self.verificar_fim_de_jogo(): 
            return

        active_ps = [p for p in self.players if p["active"]]
        for w in self.root.winfo_children(): w.destroy()
        canvas = tk.Canvas(self.root, bg=Theme.BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self.root.update()
        w_mid, h_mid = self.root.winfo_width() // 2, self.root.winfo_height() // 2
        title = canvas.create_text(w_mid, h_mid, text="SORTEANDO ATACANTE...", fill="white", font=("Segoe UI", 45, "bold"))
        
        for i in range(15):
            p_sorteado = random.choice(active_ps)
            canvas.itemconfig(title, text=f"J {p_sorteado['id']}\n{p_sorteado['main_cat'].upper()}", fill=p_sorteado['color'], justify="center")
            self.root.update()
            time.sleep(0.07)
            
        self.current_player_id = p_sorteado["id"]
        p_sorteado["time"] = 45.0  
        self.root.after(500, self.render_arena)

    def render_arena(self):
        if self.verificar_fim_de_jogo():
            return
            
        for w in self.root.winfo_children(): w.destroy()
        self.ranking_widgets.clear() # Limpa o cache antigo
        
        # Ajustado para 450 para comportar o nome das categorias perfeitamente
        side_frame = tk.Frame(self.root, width=450, bg=Theme.CARD)
        side_frame.pack(side="right", fill="y")
        side_frame.pack_propagate(False)
        
        utils_frame = tk.Frame(side_frame, bg=Theme.CARD)
        utils_frame.pack(fill="x", pady=10, padx=10)
        
        tk.Button(utils_frame, text="💾 GUARDAR PROGRESSO", font=("Segoe UI", 10, "bold"), bg="#1a233a", fg=Theme.ACCENT, 
                  command=self.salvar_jogo_caixa_dialogo).pack(fill="x", pady=4)
        tk.Button(utils_frame, text="↩ RETORNAR AO MENU", font=("Segoe UI", 10, "bold"), bg="#2a1a1a", fg=Theme.WARN, 
                  command=self.main_menu).pack(fill="x", pady=4)
        
        tk.Label(side_frame, text="RANKING COMPLETO (m²) & CATEGORIAS", font=("Segoe UI", 13, "bold"), bg=Theme.CARD, fg=Theme.ACCENT).pack(pady=10)
        container = tk.Frame(side_frame, bg=Theme.CARD)
        container.pack(fill="both", expand=True)
        
        self.rank_canvas = tk.Canvas(container, bg=Theme.CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.rank_canvas.yview)
        self.scrollable_rank = tk.Frame(self.rank_canvas, bg=Theme.CARD)
        self.scrollable_rank.bind("<Configure>", lambda e: self.rank_canvas.configure(scrollregion=self.rank_canvas.bbox("all")))
        self.rank_canvas.create_window((0, 0), window=self.scrollable_rank, anchor="nw")
        self.rank_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Adiciona rolagem do rato no menu de ranking lateral
        def _on_mousewheel_rank(event):
            self.rank_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.rank_canvas.bind_all("<MouseWheel>", _on_mousewheel_rank)
        
        self.rank_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        main = tk.Frame(self.root, bg=Theme.BG)
        main.pack(expand=True, fill="both")
        self.status_lbl = tk.Label(main, font=("Segoe UI", 20, "bold"), bg=Theme.BG)
        self.status_lbl.pack(pady=5)
        
        grid_f = tk.Frame(main, bg=Theme.BG)
        grid_f.pack(expand=True)
        
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                btn = tk.Button(grid_f, width=11, height=3, relief="flat", font=Theme.BOARD_FONT, wraplength=80, justify="center",
                                command=lambda r=r, c=c: self.on_click_cell(r, c))
                btn.grid(row=r, column=c, padx=2, pady=2)
                self.grid_widgets[(r, c)] = btn
        self.update_ui()

    def update_ui(self):
        atk = self.get_player_by_id(self.current_player_id)
        if not atk:
            return
        self.status_lbl.config(text=f"NO PALCO: J {atk['id']} | {atk['main_cat'].upper()} | {atk['time']:.1f}s", fg=atk['color'])
        
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                cell = self.board[r][c]
                is_atk = (cell["owner"]["id"] == self.current_player_id)
                nome_cat = cell['cat']
                p_owner = cell["owner"]
                
                txt = f"J{p_owner['id']}\n{nome_cat[:10]}"
                bg_color = p_owner['color']
                
                if is_atk:
                    self.grid_widgets[(r, c)].config(text=txt, bg=bg_color, fg="white", highlightbackground=Theme.ACCENT, highlightthickness=3, relief="solid")
                else:
                    self.grid_widgets[(r, c)].config(text=txt, bg=bg_color, fg="white", highlightthickness=0, relief="flat")
        
        # IMPLEMENTAÇÃO DO MENU DINÂMICO DE CATEGORIAS E RANKING (Otimizado sem vazamento de memória)
        ranked = sorted([p for p in self.players if p["active"]], key=lambda x: x["cells"], reverse=True)
        
        # Reutilizar ou criar frames para evitar sobrecarga do Tkinter
        for i, p in enumerate(ranked):
            # Procura a categoria atual real do que ele defende no tabuleiro
            categoria_atual = "Eliminado"
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    if self.board[r][c]["owner"]["id"] == p["id"]:
                        categoria_atual = self.board[r][c]["cat"]
                        break
                if categoria_atual != "Eliminado": break

            texto_ranking = f"#{i+1} J{p['id']} ({p['cells']} m²) - {categoria_atual}"
            
            if i < len(self.ranking_widgets):
                # Atualiza item existente
                item_frame, lbl_text, color_badge = self.ranking_widgets[i]
                lbl_text.config(text=texto_ranking)
                color_badge.config(bg=p['color'])
            else:
                # Instancia novo item caso a lista cresça
                item = tk.Frame(self.scrollable_rank, bg=Theme.CARD, pady=4)
                item.pack(fill="x", padx=5)
                
                lbl = tk.Label(item, text=texto_ranking, font=("Segoe UI", 9, "bold"), fg="white", bg=Theme.CARD, anchor="w")
                lbl.pack(side="left", fill="x", expand=True)
                
                badge = tk.Frame(item, bg=p['color'], width=15, height=15)
                badge.pack(side="right", padx=5)
                
                self.ranking_widgets.append((item, lbl, badge))
                
        # Remove excedentes se houver menos jogadores ativos do que o cache guardou
        while len(self.ranking_widgets) > len(ranked):
            item_frame, _, _ = self.ranking_widgets.pop()
            item_frame.destroy()

    def on_click_cell(self, r, c):
        if self.duel_active:
            return
            
        target_cell = self.board[r][c]
        target_player = target_cell["owner"]
        attacker = self.get_player_by_id(self.current_player_id)
        
        if target_player["id"] == attacker["id"]:
            messagebox.showwarning("Aviso", "Não podes atacar o teu próprio território!")
            return
            
        # Verificar vizinhança (se a célula clicada faz fronteira com o atacante)
        is_neighbor = False
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                if self.board[nr][nc]["owner"]["id"] == attacker["id"]:
                    is_neighbor = True
                    break
                    
        if not is_neighbor:
            messagebox.showwarning("Fronteira Inválida", "Só podes atacar territórios que façam fronteira com o teu império!")
            return
            
        self.iniciar_duelo(attacker, target_player, target_cell["cat"])

    # =================================================================
    # SISTEMA DE DUELOS E INTERFACE DE PERGUNTAS
    # =================================================================
    def iniciar_duelo(self, attacker, defender, categoria_duelo):
        self.duel_active = True
        
        # Resetar timers de duelo
        attacker["time"] = 45.0
        defender["time"] = 45.0
        
        self.duel_window = tk.Toplevel(self.root)
        self.duel_window.title("PALCO DE DUELO - COMBATE EM TEMPO REAL")
        self.duel_window.state('zoomed')
        self.duel_window.configure(bg=Theme.BG)
        self.duel_window.grab_set()
        
        # Bloquear fecho acidental
        self.duel_window.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Painel Superior de Categoria
        cat_frame = tk.Frame(self.duel_window, bg=Theme.CARD, height=60)
        cat_frame.pack(fill="x", side="top")
        tk.Label(cat_frame, text=f"CATEGORIA EM DISPUTA: {categoria_duelo.upper()}", font=("Segoe UI", 16, "bold"), fg=Theme.ACCENT, bg=Theme.CARD).pack(pady=15)
        
        # Área Central Split (Cronómetros)
        timers_frame = tk.Frame(self.duel_window, bg=Theme.BG)
        timers_frame.pack(fill="x", pady=20)
        
        # Atacante
        self.atk_box = tk.Frame(timers_frame, bg=Theme.CARD, padx=20, pady=10)
        self.atk_box.pack(side="left", expand=True, fill="both", padx=40)
        tk.Label(self.atk_box, text=f"ATACANTE (J{attacker['id']})", font=("Segoe UI", 12, "bold"), fg="white", bg=Theme.CARD).pack()
        self.atk_clock = tk.Label(self.atk_box, text="45.0", font=Theme.CLOCK, fg="#00FF66", bg=Theme.CARD)
        self.atk_clock.pack(pady=5)
        
        # Defensor
        self.def_box = tk.Frame(timers_frame, bg=Theme.CARD, padx=20, pady=10)
        self.def_box.pack(side="right", expand=True, fill="both", padx=40)
        tk.Label(self.def_box, text=f"DEFENSOR (J{defender['id']})", font=("Segoe UI", 12, "bold"), fg="white", bg=Theme.CARD).pack()
        self.def_clock = tk.Label(self.def_box, text="45.0", font=Theme.CLOCK, fg="#00FF66", bg=Theme.CARD)
        self.def_clock.pack(pady=5)
        
        # Zona da Pergunta Ativa
        self.qa_frame = tk.Frame(self.duel_window, bg=Theme.CARD, pady=20, padx=20, highlightbackground="#222", highlightthickness=1)
        self.qa_frame.pack(fill="both", expand=True, padx=40, pady=10)
        
        self.lbl_turno_de = tk.Label(self.qa_frame, text="", font=("Segoe UI", 14, "bold"), bg=Theme.CARD)
        self.lbl_turno_de.pack()
        
        self.lbl_pergunta = tk.Label(self.qa_frame, text="Preparar Palco...", font=("Segoe UI", 16), fg=Theme.TEXT, bg=Theme.CARD, wraplength=800, justify="center")
        self.lbl_pergunta.pack(pady=20)
        
        # Input de resposta
        self.entry_resposta = tk.Entry(self.qa_frame, font=("Segoe UI", 16), bg=Theme.BG, fg="white", insertbackground="white", justify="center", width=40)
        self.entry_resposta.pack(pady=10)
        self.entry_resposta.bind("<Return>", lambda e: self.submeter_resposta())
        self.entry_resposta.config(state="disabled")
        
        # Botões de Controlo
        ctrl_frame = tk.Frame(self.qa_frame, bg=Theme.CARD)
        ctrl_frame.pack(pady=10)
        
        self.btn_responder = tk.Button(ctrl_frame, text="✓ ENVIAR (ENTER)", font=("Segoe UI", 11, "bold"), bg="#00FF66", fg="black", command=self.submeter_resposta, state="disabled", width=18)
        self.btn_responder.pack(side="left", padx=10)
        
        self.btn_passar = tk.Button(ctrl_frame, text="⏭ PASSAR / SKIP (-3s)", font=("Segoe UI", 11, "bold"), bg=Theme.WARN, fg="black", command=self.passar_pergunta, state="disabled", width=18)
        self.btn_passar.pack(side="left", padx=10)
        
        # Configurações internas do duelo
        self.p_atual = attacker
        self.p_passivo = defender
        self.atk_ref = attacker
        self.def_ref = defender
        self.cat_duelo = categoria_duelo
        self.pergunta_ativa = None
        
        # Iniciar loop de contagem decrescente
        self.last_time = time.time()
        self.duelo_loop()
        
        # Carregar primeira pergunta após uma breve pausa
        self.duel_window.after(1500, self.proxima_pergunta)

    def duelo_loop(self):
        if not self.duel_active:
            return
            
        agora = time.time()
        delta = agora - self.last_time
        self.last_time = agora
        
        if not self.ia_checking:
            self.p_atual["time"] -= delta
            if self.p_atual["time"] <= 0:
                self.p_atual["time"] = 0
                self.atualizar_clocks_interface()
                self.finalizar_duelo_por_timeout()
                return
                
        self.atualizar_clocks_interface()
        self.loop_id = self.duel_window.after(50, self.duelo_loop)

    def atualizar_clocks_interface(self):
        self.atk_clock.config(text=f"{self.atk_ref['time']:.1f}")
        self.def_clock.config(text=f"{self.def_ref['time']:.1f}")
        
        # Alertas visuais de tempo crítico
        if self.atk_ref["time"] < 10: self.atk_clock.config(fg="#FF3333")
        if self.def_ref["time"] < 10: self.def_clock.config(fg="#FF3333")

    def proxima_pergunta(self):
        if not self.duel_active:
            return
            
        self.entry_resposta.config(state="normal")
        self.entry_resposta.delete(0, tk.END)
        self.entry_resposta.focus_set()
        self.btn_responder.config(state="normal")
        self.btn_passar.config(state="normal")
        
        # Destacar visualmente de quem é o turno
        if self.p_atual["id"] == self.atk_ref["id"]:
            self.atk_box.config(highlightbackground=Theme.ACCENT, highlightthickness=3)
            self.def_box.config(highlightthickness=0)
            self.lbl_turno_de.config(text=f"TURNO DE RESPOSTA: JOGADOR {self.p_atual['id']} (ATACANTE)", fg=Theme.ACCENT)
        else:
            self.def_box.config(highlightbackground=Theme.ACCENT, highlightthickness=3)
            self.atk_box.config(highlightthickness=0)
            self.lbl_turno_de.config(text=f"TURNO DE RESPOSTA: JOGADOR {self.p_atual['id']} (DEFENSOR)", fg=Theme.ACCENT)
            
        self.pergunta_ativa = puxar_pergunta(self.dados_base, self.pilhas, self.cat_duelo)
        self.lbl_pergunta.config(text=self.pergunta_ativa["pergunta"])

    def submeter_resposta(self):
        if self.ia_checking or not self.duel_active:
            return
            
        resp = self.entry_resposta.get().strip()
        if not resp:
            return
            
        self.ia_checking = True
        self.entry_resposta.config(state="disabled")
        self.btn_responder.config(state="disabled")
        self.btn_passar.config(state="disabled")
        
        # Executar validação em Thread separada para não congelar o cronómetro/UI
        threading.Thread(target=self.thread_validar_resposta, args=(resp,), daemon=True).start()

    def thread_validar_resposta(self, resposta_utilizador):
        pergunta = self.pergunta_ativa["pergunta"]
        gabarito = self.pergunta_ativa["resposta"]
        
        correto = AIJudge.verificar_resposta(pergunta, gabarito, resposta_utilizador)
        
        # Sincronizar de volta com a Main Thread do Tkinter
        self.duel_window.after(0, lambda: self.processar_resultado_validacao(correto))

    def processar_resultado_validacao(self, correto):
        self.ia_checking = False
        if not self.duel_active:
            return
            
        if correto:
            self.p_atual["certas"] += 1
            # Inverter turnos
            self.p_atual, self.p_passivo = self.p_passivo, self.p_atual
            self.proxima_pergunta()
        else:
            self.p_atual["erradas"] += 1
            # Resposta errada força nova pergunta para o mesmo jogador (perda de tempo por erro)
            self.proxima_pergunta()

    def pasar_pergunta(self):
        # Correção do nome interno chamado pelo botão (passar_pergunta)
        self.passar_pergunta()

    def passar_pergunta(self):
        if self.ia_checking or not self.duel_active:
            return
            
        # Penalização por Skip: -3 segundos
        self.p_atual["time"] = max(0, self.p_atual["time"] - 3.0)
        self.p_atual["erradas"] += 1 # Conta como erro para fins estatísticos
        self.atualizar_clocks_interface()
        
        if self.p_atual["time"] <= 0:
            self.finalizar_duelo_por_timeout()
            return
            
        self.proxima_pergunta()

    def finalizar_duelo_por_timeout(self):
        self.duel_active = False
        if self.loop_id:
            self.duel_window.after_cancel(self.loop_id)
            
        vencedor = self.p_passivo
        derrotado = self.p_atual
        
        vencedor["vitorias_duelo"] += 1
        derrotado["active"] = False
        
        messagebox.showinfo("FIM DO DUELO", f"O tempo do Jogador {derrotado['id']} esgotou!\n\nJOGADOR {vencedor['id']} VENCE O DUELO!")
        
        # Transferência de Território
        celulas_conquistadas = 0
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.board[r][c]["owner"]["id"] == derrotado["id"]:
                    self.board[r][c]["owner"] = vencedor
                    celulas_conquistadas += 1
                    
        vencedor["cells"] += celulas_conquistadas
        if vencedor["cells"] > vencedor["max_cells"]:
            vencedor["max_cells"] = vencedor["cells"]
            
        # Atualizar ficheiros globais de estatísticas imediatamente
        StatsEngine.atualizar_e_salvar_graficos(self.players)
        StatsEngine.exportar_estatisticas_csv(self.players)
        
        self.duel_window.destroy()
        
        # Lógica de escolha de continuidade para o Vencedor
        self.oferecer_escolha_continuidade(vencedor)

    def ofrecer_escolha_continuidade(self, vencedor):
        if self.verificar_fim_de_jogo():
            return

        # Criar caixa de diálogo customizada para escolha do fluxo
        self.choice_window = tk.Toplevel(self.root)
        self.choice_window.title("DECISÃO DO VENCEDOR")
        self.choice_window.geometry("450x250")
        self.choice_window.configure(bg=Theme.CARD)
        self.choice_window.grab_set()
        self.choice_window.protocol("WM_DELETE_WINDOW", lambda: None)
        
        tk.Label(self.choice_window, text=f"Parabéns JOGADOR {vencedor['id']}!", font=("Segoe UI", 14, "bold"), fg=Theme.ACCENT, bg=Theme.CARD).pack(pady=15)
        tk.Label(self.choice_window, text="O que desejas fazer de seguida?", font=("Segoe UI", 11), fg=Theme.TEXT, bg=Theme.CARD).pack(pady=5)
        
        # Opção 1: Continuar no palco com o ID vencedor
        tk.Button(self.choice_window, text="CONTINUAR NO PALCO (ATACAR OUTRO)", font=("Segoe UI", 11, "bold"), bg="#00FF66", fg="black", pady=8, cursor="hand2", width=35,
                  command=lambda: self.decidir_fluxo_continuidade(vencedor["id"], continuar=True)).pack(pady=8)
                  
        # Opção 2: Voltar para o tabuleiro e sortear um novo atacante aleatório
        tk.Button(self.choice_window, text="REGRESSAR AO TABULEIRO (SORTEIO ALEATÓRIO)", font=("Segoe UI", 11, "bold"), bg=Theme.WARN, fg="black", pady=8, cursor="hand2", width=35,
                  command=lambda: self.decidir_fluxo_continuidade(vencedor["id"], continuar=False)).pack(pady=8)

    def decidir_fluxo_continuidade(self, vencedor_id, continuar):
        self.choice_window.destroy()
        if continuar:
            self.current_player_id = vencedor_id
            self.render_arena()
        else:
            self.pick_random_attacker()


# =================================================================
# ENTRADA PRINCIPAL DA APLICAÇÃO
# =================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = TheFloorGame(root)
    root.mainloop()