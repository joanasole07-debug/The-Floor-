import tkinter as tk
from tkinter import messagebox, ttk
import random
import time
import json
import os
import csv
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

import ollama

# =================================================================
# CONFIGURAÇÕES DO TABULEIRO
# =================================================================
GRID_SIZE = 10  
OLLAMA_MODEL = "llama3" 

# =================================================================
# 1. GESTÃO DE DADOS E INFRAESTRUTURA
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
                {"pergunta": "Em que ano ocorreu a Revolução dos Cravos?", "resposta": "1974"}
            ],
            "Geografia do Continente Europeu": [
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
# LÓGICA DE VALIDAÇÃO INTELIGENTE (IA TOLERANTE A SIMPLIFICAÇÕES)
# =================================================================
def verificar_resposta_com_ia(pergunta, resposta_esperada, resposta_utilizador):
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
    3. Só deves rejeitar se a resposta do jogador for factualmente diferente ou errada em relação ao contexto da pergunta.
    
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
        dados_resposta = json.loads(response['message']['content'])
        status = dados_resposta.get("resultado", "INCORRETO").strip().upper()
        
        return "CORRETO" in status
    except Exception as e:
        print(f"Erro na IA: {e}. Usando verificação por contenção.")
        return resp_utilizador_clean in resp_esperada_clean or resp_esperada_clean in resp_utilizador_clean

# =================================================================
# 2. INTERFACE E LÓGICA DO JOGO
# =================================================================
class Theme:
    BG = "#05070A"; CARD = "#10141D"; ACCENT = "#00F2FF"; TEXT = "#E1E7EF"; WARN = "#FFCC00"
    CLOCK = ("Courier New", 45, "bold")
    BOARD_FONT = ("Segoe UI", 8, "bold") 

class TheFloorGame:
    def __init__(self, root):
        self.root = root
        self.root.title("THE FLOOR PORTUGAL - CONTABILIZAÇÃO DE SKIPS")
        self.root.state('zoomed') 
        self.root.configure(bg=Theme.BG)
        
        self.dados_base, self.pilhas = carregar_base_dados()
        self.all_cats = list(self.dados_base.keys())
        self.grid_widgets = {}
        self.main_menu()

    def main_menu(self):
        for w in self.root.winfo_children(): w.destroy()
        frame = tk.Frame(self.root, bg=Theme.BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(frame, text="THE FLOOR", font=("Impact", 100), fg=Theme.ACCENT, bg=Theme.BG).pack()
        tk.Button(frame, text="INICIAR COMPETIÇÃO", font=("Segoe UI", 18, "bold"), bg=Theme.ACCENT, 
                  command=self.setup_game, padx=50, pady=20, cursor="hand2").pack(pady=40)

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
        
        self.atualizar_e_salvar_graficos()
        self.exportar_estatisticas_csv()
        self.pick_random_attacker()

    def pick_random_attacker(self):
        active_ps = [p for p in self.players if p["active"]]
        if len(active_ps) <= 1:
            winner = active_ps[0] if active_ps else None
            messagebox.showinfo("FIM", f"O GRANDE VENCEDOR É O JOGADOR {winner['id']}!")
            self.main_menu()
            return

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
        for w in self.root.winfo_children(): w.destroy()
        
        side_frame = tk.Frame(self.root, width=380, bg=Theme.CARD)
        side_frame.pack(side="right", fill="y")
        side_frame.pack_propagate(False)
        
        tk.Label(side_frame, text="RANKING COMPLETO (m²)", font=("Segoe UI", 14, "bold"), bg=Theme.CARD, fg=Theme.ACCENT).pack(pady=15)
        container = tk.Frame(side_frame, bg=Theme.CARD)
        container.pack(fill="both", expand=True)
        
        self.rank_canvas = tk.Canvas(container, bg=Theme.CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.rank_canvas.yview)
        self.scrollable_rank = tk.Frame(self.rank_canvas, bg=Theme.CARD)
        self.scrollable_rank.bind("<Configure>", lambda e: self.rank_canvas.configure(scrollregion=self.rank_canvas.bbox("all")))
        self.rank_canvas.create_window((0, 0), window=self.scrollable_rank, anchor="nw")
        self.rank_canvas.configure(yscrollcommand=scrollbar.set)
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
        self.status_lbl.config(text=f"NO PALCO: J {atk['id']} | {atk['main_cat'].upper()} | {atk['time']:.1f}s", fg=atk['color'])
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                cell = self.board[r][c]
                is_atk = (cell["owner"]["id"] == self.current_player_id)
                
                nome_cat = cell['cat'] if len(cell['cat']) <= 14 else cell['cat'][:12] + ".."
                self.grid_widgets[(r, c)].config(
                    text=f"J{cell['owner']['id']}\n{nome_cat}", 
                    bg=cell['owner']['color'], fg="white" if is_atk else "black",
                    highlightthickness=2 if is_atk else 0, highlightbackground="white"
                )
        for w in self.scrollable_rank.winfo_children(): w.destroy()
        sorted_players = sorted(self.players, key=lambda x: (not x["active"], -x["cells"], x["id"]))
        for p in sorted_players:
            color = p["color"] if p["active"] else "#444444"
            st = "" if p["active"] else " [ELIMINADO]"
            tk.Label(self.scrollable_rank, text=f"J {p['id']:03} | {p['cells']:2}m² | {p['main_cat']}{st}", 
                     font=("Consolas", 9), bg=Theme.CARD, fg=color if p["active"] else "#777777", anchor="w").pack(fill="x", padx=10, pady=1)

    def on_click_cell(self, r, c):
        target_cell = self.board[r][c]
        if target_cell["owner"]["id"] == self.current_player_id: return
        
        adj = False
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                if self.board[nr][nc]["owner"]["id"] == self.current_player_id: 
                    adj = True
                    break
        if adj: self.start_duel(r, c)
        else: messagebox.showwarning("Aviso", "Podes apenas atacar territórios adjacentes ao teu império!")

    def start_duel(self, r, c):
        self.duel_active = True
        self.defender = self.board[r][c]["owner"]
        self.attacker = self.get_player_by_id(self.current_player_id)
        self.duel_cat = self.board[r][c]["cat"] 
        self.turn_p = self.attacker
        
        self.d_win = tk.Toplevel(self.root)
        self.d_win.title("DUELO COM ARBITRAGEM INTELIGENTE")
        self.d_win.geometry("650x750")
        self.d_win.configure(bg=Theme.CARD)
        self.d_win.grab_set()
        
        tk.Label(self.d_win, text=f"CATEGORIA: {self.duel_cat.upper()}", font=("Segoe UI", 20, "bold"), bg=Theme.CARD, fg=Theme.ACCENT).pack(pady=15)
        self.lbl_t = tk.Label(self.d_win, text="45.0", font=Theme.CLOCK, bg=Theme.CARD, fg="white")
        self.lbl_t.pack(pady=5)
        self.lbl_feedback = tk.Label(self.d_win, text="A IA aceita respostas completas ou simplificadas de forma inteligente.", font=("Segoe UI", 11, "italic"), bg=Theme.CARD, fg=Theme.WARN)
        self.lbl_feedback.pack(pady=5)
        self.lbl_q = tk.Label(self.d_win, text="", font=("Segoe UI", 16), fg="white", bg=Theme.CARD, wraplength=550)
        self.lbl_q.pack(pady=15)
        
        self.ent = tk.Entry(self.d_win, font=("Segoe UI", 26), justify="center")
        self.ent.pack(pady=10)
        self.ent.focus_set()
        self.ent.bind("<Return>", lambda e: self.check_answer())
        
        tk.Button(self.d_win, text="PASSAR / SKIP (-5s)", bg=Theme.WARN, font=("Segoe UI", 12, "bold"), 
                  command=self.skip_question, cursor="hand2", padx=25, pady=10).pack(pady=15)
        
        self.last_tick = time.time()
        self.next_question()
        self.duel_loop()

    def next_question(self, feedback=""):
        self.curr_q = puxar_pergunta(self.dados_base, self.pilhas, self.duel_cat)
        self.lbl_q.config(text=f"VEZ DE: J {self.turn_p['id']}\n\n{self.curr_q['pergunta']}")
        self.lbl_t.config(fg=self.turn_p['color'])
        self.lbl_feedback.config(text=feedback, fg=Theme.WARN)
        self.ent.delete(0, tk.END)

    def skip_question(self):
        """ Penaliza com tempo e adiciona falha direta à contagem do gráfico (barra vermelha) """
        resp = self.curr_q['resposta']
        self.turn_p["time"] -= 5.0
        
        # AJUSTE SOLICITADO: O skip agora incrementa diretamente as estatísticas de erro.
        self.turn_p["erradas"] += 1 
        
        self.next_question(f"PASSOU! A RESPOSTA ERA: {resp.upper()}")

    def check_answer(self):
        resposta_utilizador = self.ent.get().strip()
        if not resposta_utilizador: return
        
        self.lbl_feedback.config(text="A analisar resposta semanticamente...", fg="#00F2FF")
        self.d_win.update()
        
        ia_aprovou = verificar_resposta_com_ia(self.curr_q['pergunta'], self.curr_q['resposta'], resposta_utilizador)
        
        if ia_aprovou:
            self.turn_p["certas"] += 1
            self.turn_p = self.defender if self.turn_p == self.attacker else self.attacker
            self.next_question("")
        else:
            self.turn_p["erradas"] += 1
            self.lbl_feedback.config(text="ANÁLISE DA IA: INCORRETA! TENTA DE NOVO.", fg="#FF3333")
            self.ent.delete(0, tk.END)

    def duel_loop(self):
        if not self.duel_active: return
        now = time.time()
        dt = now - self.last_tick
        self.last_tick = now
        
        self.turn_p["time"] -= dt
        self.lbl_t.config(text=f"{max(0, self.turn_p['time']):.1f}")
        
        if self.turn_p["time"] <= 0:
            winner = self.defender if self.turn_p == self.attacker else self.attacker
            self.resolve_duel(winner)
        else: 
            self.d_win.after(50, self.duel_loop)

    def resolve_duel(self, winner):
        self.duel_active = False
        loser = self.defender if winner == self.attacker else self.attacker
        winner["vitorias_duelo"] += 1
        
        messagebox.showinfo("Fim do Duelo", f"VITÓRIA!\nO J {winner['id']} conquistou o império de J {loser['id']}.")
        
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.board[r][c]["owner"]["id"] == loser["id"]:
                    self.board[r][c]["owner"] = winner
                    self.board[r][c]["cat"] = winner["main_cat"]
        
        loser["active"] = False
        self.d_win.destroy()
        
        for p in self.players:
            p["cells"] = sum(1 for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.board[r][c]["owner"]["id"] == p["id"])
            if p["cells"] > p["max_cells"]:
                p["max_cells"] = p["cells"]
        
        self.atualizar_e_salvar_graficos()
        self.exportar_estatisticas_csv()
        
        if messagebox.askyesno("Estratégia", f"J {winner['id']}, desejas CONTINUAR?"):
            winner["time"] = 45.0
            self.current_player_id = winner["id"]
            self.render_arena()
        else: 
            self.pick_random_attacker()

    # =================================================================
    # EXPORTAÇÃO DE EXCEL EM FORMATO DE TABELA REAL (; SEPARATOR)
    # =================================================================
    def exportar_estatisticas_csv(self):
        pasta_do_script = os.path.dirname(os.path.abspath(__file__))
        caminho_csv = os.path.join(pasta_do_script, 'relatorio_jogadores.csv')
        
        headers = ["ID_Jogador", "Categoria_Inicial", "Estado", "Territorio_Atual_m2", "Tamanho_Maximo_Atingido", "Respostas_Certas", "Respostas_Erradas_Com_Skips", "Duelos_Vencidos"]
        try:
            with open(caminho_csv, mode='w', encoding='utf-8-sig', newline='') as f:
                f.write("sep=;\n")
                writer = csv.writer(f, delimiter=';')
                writer.writerow(headers)
                for p in self.players:
                    estado = "ATIVO" if p["active"] else "ELIMINADO"
                    writer.writerow([
                        p["id"], p["main_cat"], estado, p["cells"], 
                        p["max_cells"], p["certas"], p["erradas"], p["vitorias_duelo"]
                    ])
        except Exception as e:
            print(f"Erro ao exportar CSV para Excel: {e}")

    # =================================================================
    # GRÁFICOS ATUALIZADOS (SKIPS REFLETEM NAS BARRAS VERMELHAS)
    # =================================================================
    def atualizar_e_salvar_graficos(self):
        pasta_do_script = os.path.dirname(os.path.abspath(__file__))
        
        jogadores_ranqueados = sorted(self.players, key=lambda x: x["cells"], reverse=True)
        top_10 = jogadores_ranqueados[:10]
        
        if not top_10: return

        # --- GRÁFICO 1: TERRITÓRIOS DO TOP 10 ---
        labels_t = [f"J{p['id']}" for p in top_10]
        territorios = [p["cells"] for p in top_10]
        cores_t = [p["color"] for p in top_10]

        plt.figure(1, figsize=(8, 4))
        plt.clf() 
        plt.bar(labels_t, territorios, color=cores_t)
        plt.title('Top 10 Maiores Impérios Ativos (m²)')
        plt.ylabel('Células')
        plt.tight_layout()
        plt.savefig(os.path.join(pasta_do_script, 'relatorio_ranking_global.png'))
        plt.close(1)

        # --- GRÁFICO 2: PERFORMANCE (BARRAS VERDE E VERMELHA COM SKIPS) ---
        ids_jogadores = [f"J{p['id']}\n({p['main_cat'][:8]}..)" for p in top_10]
        certas = [p["certas"] for p in top_10]
        erradas = [p["erradas"] for p in top_10] # Aqui já estão incluídos os skips efetuados
        
        x = range(len(ids_jogadores))
        width = 0.35
        
        plt.figure(2, figsize=(11, 5))
        plt.clf()
        
        plt.bar([i - width/2 for i in x], certas, width, label='Certas', color='#00FF66') 
        plt.bar([i + width/2 for i in x], erradas, width, label='Erradas (Inc. Skips)', color='#FF3333') 
        
        plt.title('Histórico de Respostas - Top 10 Jogadores (Skips Incluídos nos Erros)', fontsize=12, fontweight='bold')
        plt.xticks(x, ids_jogadores, fontsize=9)
        plt.ylabel('Quantidade de Respostas')
        plt.legend(loc='upper right')
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        
        plt.gca().yaxis.get_major_locator().set_params(integer=True)
        
        plt.tight_layout()
        plt.savefig(os.path.join(pasta_do_script, 'relatorio_respostas_top10.png'))
        plt.close(2)

    def get_player_by_id(self, pid):
        return next(p for p in self.players if p["id"] == pid)

if __name__ == "__main__":
    root = tk.Tk()
    app = TheFloorGame(root)
    root.mainloop()