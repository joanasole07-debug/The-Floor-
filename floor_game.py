import tkinter as tk
from tkinter import messagebox, ttk
import random
import time
import json
import os
import matplotlib
# Força o Matplotlib a correr em background sem abrir janelas pop-up chatas a cada segundo
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

# =================================================================
# 1. GESTÃO DE DADOS
# =================================================================
def carregar_base_dados():
    file_path = "perguntas.json"
    if not os.path.exists(file_path):
        exemplo = {
            "Culinária Tradicional Portuguesa": [{"pergunta": "Qual o ingrediente principal do Bacalhau à Brás?", "resposta": "Bacalhau"}],
            "História de Portugal e Descobrimentos": [{"pergunta": "Quem chegou à Índia em 1498?", "resposta": "Vasco da Gama"}],
            "Geografia do Continente Europeu": [{"pergunta": "Qual a capital da França?", "resposta": "Paris"}]
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
# 2. INTERFACE E LÓGICA DO JOGO
# =================================================================
class Theme:
    BG = "#05070A"; CARD = "#10141D"; ACCENT = "#00F2FF"; TEXT = "#E1E7EF"; WARN = "#FFCC00"
    CLOCK = ("Courier New", 45, "bold")
    BOARD_FONT = ("Segoe UI", 9, "bold")

class TheFloorGame:
    def __init__(self, root):
        self.root = root
        self.root.title("THE FLOOR PORTUGAL - EDIÇÃO COMPLETA")
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
        tk.Label(frame, text="THE FLOOR", font=("Impact", 120), fg=Theme.ACCENT, bg=Theme.BG).pack()
        tk.Button(frame, text="INICIAR COMPETIÇÃO", font=("Segoe UI", 20, "bold"), bg=Theme.ACCENT, 
                  command=self.setup_game, padx=60, pady=25, cursor="hand2").pack(pady=40)

    def setup_game(self):
        pool_cats = (self.all_cats * (100 // len(self.all_cats) + 1))[:100]
        random.shuffle(pool_cats)
        
        self.players = []
        self.board = []
        idx = 1
        for r in range(10):
            row = []
            for c in range(10):
                color = f'#{random.randint(40,210):02x}{random.randint(40,210):02x}{random.randint(40,210):02x}'
                cat_nome = pool_cats[idx-1]
                p = {"id": idx, "main_cat": cat_nome, "color": color, "time": 45.0, "active": True, "cells": 1}
                self.players.append(p)
                row.append({"owner": p, "cat": cat_nome})
                idx += 1
            self.board.append(row)
        
        # Guardar os gráficos iniciais com o tabuleiro a zeros/1 célula cada
        self.atualizar_e_salvar_graficos()
        self.pick_random_attacker()

    def pick_random_attacker(self):
        active_ps = [p for p in self.players if p["active"]]
        if len(active_ps) <= 1:
            winner = active_ps[0] if active_ps else None
            messagebox.showinfo("FIM", f"O GRANDE VENCEDOR É O J {winner['id']}!")
            self.main_menu()
            return

        for w in self.root.winfo_children(): w.destroy()
        canvas = tk.Canvas(self.root, bg=Theme.BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self.root.update()
        w_mid, h_mid = self.root.winfo_width() // 2, self.root.winfo_height() // 2
        title = canvas.create_text(w_mid, h_mid, text="SORTEANDO ATACANTE...", fill="white", font=("Segoe UI", 45, "bold"))
        
        for i in range(20):
            p = random.choice(active_ps)
            canvas.itemconfig(title, text=f"J {p['id']}\n{p['main_cat'].upper()}", fill=p['color'], justify="center")
            self.root.update(); time.sleep(0.07)
            
        self.current_player_id = p["id"]
        p["time"] = 45.0 
        self.root.after(500, self.render_arena)

    def render_arena(self):
        for w in self.root.winfo_children(): w.destroy()
        
        side_frame = tk.Frame(self.root, width=550, bg=Theme.CARD)
        side_frame.pack(side="right", fill="y")
        side_frame.pack_propagate(False)
        
        tk.Label(side_frame, text="RANKING COMPLETO (m²)", font=("Segoe UI", 16, "bold"), bg=Theme.CARD, fg=Theme.ACCENT).pack(pady=20)
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
        self.status_lbl = tk.Label(main, font=("Segoe UI", 24, "bold"), bg=Theme.BG)
        self.status_lbl.pack(pady=20)
        
        grid_f = tk.Frame(main, bg=Theme.BG)
        grid_f.pack(expand=True)
        for r in range(10):
            for c in range(10):
                btn = tk.Button(grid_f, width=14, height=5, relief="flat", font=Theme.BOARD_FONT, wraplength=110, justify="center",
                                command=lambda r=r, c=c: self.on_click_cell(r, c))
                btn.grid(row=r, column=c, padx=2, pady=2)
                self.grid_widgets[(r, c)] = btn
        self.update_ui()

    def update_ui(self):
        atk = self.get_player_by_id(self.current_player_id)
        self.status_lbl.config(text=f"NO PALCO: J {atk['id']} | {atk['main_cat'].upper()} | {atk['time']:.1f}s", fg=atk['color'])
        for r in range(10):
            for c in range(10):
                cell = self.board[r][c]
                is_atk = (cell["owner"]["id"] == self.current_player_id)
                self.grid_widgets[(r, c)].config(
                    text=f"J {cell['owner']['id']}\n{cell['cat']}", 
                    bg=cell['owner']['color'], fg="white" if is_atk else "black",
                    highlightthickness=4 if is_atk else 0, highlightbackground="white"
                )
        for w in self.scrollable_rank.winfo_children(): w.destroy()
        sorted_players = sorted(self.players, key=lambda x: (not x["active"], -x["cells"], x["id"]))
        for p in sorted_players:
            color = p["color"] if p["active"] else "#444444"
            st = "" if p["active"] else " [ELIMINADO]"
            tk.Label(self.scrollable_rank, text=f"J {p['id']:03} | {p['cells']:2}m² | {p['main_cat']}{st}", 
                     font=("Consolas", 11), bg=Theme.CARD, fg=color if p["active"] else "#777777", anchor="w").pack(fill="x", padx=15, pady=2)

    def on_click_cell(self, r, c):
        target_cell = self.board[r][c]
        if target_cell["owner"]["id"] == self.current_player_id: return
        adj = False
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < 10 and 0 <= nc < 10:
                if self.board[nr][nc]["owner"]["id"] == self.current_player_id: adj = True; break
        if adj: self.start_duel(r, c)
        else: messagebox.showwarning("Aviso", "Ataca apenas territórios vizinhos!")

    def start_duel(self, r, c):
        self.duel_active = True
        self.defender = self.board[r][c]["owner"]
        self.attacker = self.get_player_by_id(self.current_player_id)
        self.duel_cat = self.board[r][c]["cat"] 
        self.turn_p = self.attacker
        
        self.d_win = tk.Toplevel(self.root)
        self.d_win.title("DUELO!")
        self.d_win.geometry("650x800")
        self.d_win.configure(bg=Theme.CARD)
        self.d_win.grab_set()
        
        tk.Label(self.d_win, text=f"CATEGORIA: {self.duel_cat.upper()}", font=("Segoe UI", 22, "bold"), bg=Theme.CARD, fg=Theme.ACCENT).pack(pady=20)
        self.lbl_t = tk.Label(self.d_win, text="45.0", font=Theme.CLOCK, bg=Theme.CARD, fg="white")
        self.lbl_t.pack(pady=5)
        self.lbl_feedback = tk.Label(self.d_win, text="", font=("Segoe UI", 12, "italic"), bg=Theme.CARD, fg=Theme.WARN)
        self.lbl_feedback.pack(pady=5)
        self.lbl_q = tk.Label(self.d_win, text="", font=("Segoe UI", 18), fg="white", bg=Theme.CARD, wraplength=550)
        self.lbl_q.pack(pady=20)
        
        self.ent = tk.Entry(self.d_win, font=("Segoe UI", 30), justify="center")
        self.ent.pack(pady=10); self.ent.focus_set()
        self.ent.bind("<Return>", lambda e: self.check_answer())
        
        tk.Button(self.d_win, text="PASSAR / SKIP (-5s)", bg=Theme.WARN, font=("Segoe UI", 14, "bold"), 
                  command=self.skip_question, cursor="hand2", padx=30, pady=15).pack(pady=20)
        
        self.last_tick = time.time()
        self.next_question()
        self.duel_loop()

    def next_question(self, feedback=""):
        self.curr_q = puxar_pergunta(self.dados_base, self.pilhas, self.duel_cat)
        self.lbl_q.config(text=f"VEZ DE: J {self.turn_p['id']}\n\n{self.curr_q['pergunta']}")
        self.lbl_t.config(fg=self.turn_p['color'])
        self.lbl_feedback.config(text=feedback)
        self.ent.delete(0, tk.END)

    def skip_question(self):
        resp = self.curr_q['resposta']
        self.turn_p["time"] -= 5.0
        self.next_question(f"RESPOSTA CORRETA ANTERIOR: {resp.upper()}")

    def check_answer(self):
        if self.ent.get().strip().lower() == self.curr_q['resposta'].strip().lower():
            self.turn_p = self.defender if self.turn_p == self.attacker else self.attacker
            self.next_question("")
        else:
            resp = self.curr_q['resposta']
            self.next_question(f"ERRASTE! A RESPOSTA ERA: {resp.upper()}")

    def duel_loop(self):
        if not self.duel_active: return
        now = time.time(); dt = now - self.last_tick; self.last_tick = now
        self.turn_p["time"] -= dt
        self.lbl_t.config(text=f"{max(0, self.turn_p['time']):.1f}")
        if self.turn_p["time"] <= 0:
            winner = self.defender if self.turn_p == self.attacker else self.attacker
            self.resolve_duel(winner)
        else: self.d_win.after(50, self.duel_loop)

    def resolve_duel(self, winner):
        self.duel_active = False
        loser = self.defender if winner == self.attacker else self.attacker
        messagebox.showinfo("Fim do Duelo", f"VITÓRIA!\nO J {winner['id']} conquistou o império de J {loser['id']}.")
        for r in range(10):
            for c in range(10):
                if self.board[r][c]["owner"]["id"] == loser["id"]:
                    self.board[r][c]["owner"] = winner
                    self.board[r][c]["cat"] = winner["main_cat"]
        loser["active"] = False
        self.d_win.destroy()
        
        # Recalcular pontuações de células
        for p in self.players:
            p["cells"] = sum(1 for r in range(10) for c in range(10) if self.board[r][c]["owner"]["id"] == p["id"])
        
        # ATUALIZAÇÃO EM TEMPO REAL: Salva novos ficheiros PNG após a conquista!
        self.atualizar_e_salvar_graficos()
        
        if messagebox.askyesno("Estratégia", f"J {winner['id']}, desejas CONTINUAR?"):
            winner["time"] = 45.0
            self.current_player_id = winner["id"]
            self.render_arena()
        else: self.pick_random_attacker()

    def atualizar_e_salvar_graficos(self):
        """ Gera os gráficos em background e força a gravação contínua na mesma pasta do script """
        jogadores_ativos = sorted([p for p in self.players if p["cells"] > 0], key=lambda x: x["cells"], reverse=True)
        if not jogadores_ativos: return

        top_10 = jogadores_ativos[:10]
        labels = [f"J{p['id']} - {p['main_cat'][:20]}" for p in top_10]
        territorios = [p["cells"] for p in top_10]
        cores = [p["color"] for p in top_10]

        # Encontrar o caminho da pasta onde o script está a correr
        pasta_do_script = os.path.dirname(os.path.abspath(__file__))
        caminho_ranking = os.path.join(pasta_do_script, 'relatorio_ranking.png')
        caminho_circular = os.path.join(pasta_do_script, 'relatorio_circular.png')

        # --- GRAVAR GRÁFICO 1: RANKING ---
        plt.figure(1, figsize=(10, 6))
        plt.clf() # Limpa o gráfico anterior para não acumular dados
        plt.barh(labels[::-1], territorios[::-1], color=cores[::-1])
        plt.title('TABULEIRO EM TEMPO REAL: Top 10 Maiores Impérios (m²)')
        plt.xlabel('Células Conquistadas')
        plt.tight_layout()
        plt.savefig(caminho_ranking)
        plt.close(1)

        # --- GRAVAR GRÁFICO 2: DISTRIBUIÇÃO ---
        plt.figure(2, figsize=(7, 7))
        plt.clf() # Limpa o gráfico anterior
        vencedor_id = jogadores_ativos[0]["id"]
        vencedor_cells = jogadores_ativos[0]["cells"]
        
        plt.pie([vencedor_cells, 100 - vencedor_cells], 
                labels=[f'Líder (J{vencedor_id})', 'Restantes'], 
                autopct='%1.1f%%', startangle=140, colors=[jogadores_ativos[0]['color'], '#d3d3d3'])
        plt.title('Percentagem de Controlo do Tabuleiro')
        plt.tight_layout()
        plt.savefig(caminho_circular)
        plt.close(2)

    def get_player_by_id(self, pid):
        return next(p for p in self.players if p["id"] == pid)

if __name__ == "__main__":
    root = tk.Tk()
    app = TheFloorGame(root)
    root.mainloop()