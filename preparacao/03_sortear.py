# Etapa 1c: embaralha os defeitos elegíveis com a semente registrada e grava ordem_sorteio.json.
# Uso: python 03_sortear.py   (rodar na pasta preparacao)
# A semente é 20261107. O embaralhamento é feito primeiro no nopCommerce e depois no ShareX, com o mesmo gerador.
# Depois, as issues são conferidas no GitHub nessa ordem (04_buscar_issues.py) até completar três por repositório.
import json, random

SEMENTE = 20261107
eleg = json.load(open('elegiveis_pre.json', encoding='utf-8'))
random.seed(SEMENTE)
ordem = {}
for r in ('nop', 'sharex'):
    lista = list(eleg[r])
    random.shuffle(lista)
    ordem[r] = lista
json.dump(ordem, open('ordem_sorteio.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
for r in ordem:
    print(r, 'primeiros na ordem do sorteio:', [x['issue'] for x in ordem[r][:6]])
