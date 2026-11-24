# Gera a Figura 9 do Capítulo 4: Top-5 e MRR no nível de arquivo, por modelo e repositório.
# Os valores são calculados a partir de piloto/resultados.csv.
# Uso, na pasta raiz do repositório:  python graficos/figura9.py   (requer matplotlib)
import csv, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELOS = [('claude', 'Claude'), ('gemini', 'Gemini'), ('nemotron', 'Nemotron'), ('cohere', 'Cohere')]
# Rótulos de perfil gravados no piloto (anteriores à nomenclatura final do TCC)
PERFIS = [('com testes', 'nopCommerce, poucos testes'), ('legado (sem testes)', 'ShareX, sem testes')]

with open(os.path.join(RAIZ, 'piloto', 'resultados.csv'), encoding='utf-8') as f:
    linhas = list(csv.DictReader(f, delimiter=';'))


def metricas(rotulo, perfil):
    ps = [int(l['pos_arquivo']) if l['pos_arquivo'] else None
          for l in linhas if l['rotulo'] == rotulo and l['perfil'] == perfil]
    top5 = round(100 * sum(1 for p in ps if p and p <= 5) / len(ps))
    mrr = round(sum(1 / p for p in ps if p) / len(ps), 2)
    return top5, mrr, len(ps)


dados = {perfil: [metricas(m, perfil) for m, _ in MODELOS] for perfil, _ in PERFIS}
CORES = ['#2a78d6', '#eb6834']
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.9), dpi=220, gridspec_kw={'width_ratios': [1.12, 1]})
w = 0.36
for ax, k, titulo, ymax, fmt in ((axs[0], 0, 'Top-5 no nível de arquivo (%)', 112, '{:.0f}'),
                                 (axs[1], 1, 'MRR no nível de arquivo', 1.12, '{:.2f}')):
    x = range(len(MODELOS))
    for j, (perfil, nome) in enumerate(PERFIS):
        n = dados[perfil][0][2]
        desloc = (-1 if j == 0 else 1) * (w / 2 + 0.01)
        barras = ax.bar([i + desloc for i in x], [v[k] for v in dados[perfil]], w, color=CORES[j], label=f'{nome} (n = {n})')
        for b in barras:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + ymax * 0.012,
                    fmt.format(b.get_height()).replace('.', ','), ha='center', va='bottom', fontsize=9, color='#0b0b0b')
    ax.set_xticks(list(x)); ax.set_xticklabels([nome for _, nome in MODELOS], color='#0b0b0b'); ax.set_ylim(0, ymax)
    ax.set_title(titulo, fontsize=10.5, color='#0b0b0b', loc='left', pad=8)
    for lado in ('top', 'right', 'left'): ax.spines[lado].set_visible(False)
    ax.spines['bottom'].set_color('#b9b8b2')
    ax.tick_params(axis='y', length=0, labelcolor='#52514e', labelsize=8.5); ax.tick_params(axis='x', length=0)
    ax.set_axisbelow(True); ax.yaxis.grid(True, color='#e6e5df', linewidth=0.8)
axs[0].set_yticks([0, 25, 50, 75, 100])
axs[1].set_yticks([0, 0.25, 0.5, 0.75, 1.0]); axs[1].set_yticklabels(['0', '0,25', '0,50', '0,75', '1,00'])
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=2, frameon=False, fontsize=9.5, bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=(0, 0.07, 1, 1))
saida = os.path.join(RAIZ, 'graficos', 'figura9.png')
fig.savefig(saida, facecolor='white')
print('Figura gravada em', saida)
