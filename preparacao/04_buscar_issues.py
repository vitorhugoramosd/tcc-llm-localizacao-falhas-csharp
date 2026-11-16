# Etapa 1d: busca no GitHub o texto das issues, na ordem do sorteio, para conferir os critérios a) e b) da seção 3.2.1.
# Uso: python 04_buscar_issues.py [quantas_por_repositorio]   (rodar na pasta preparacao; padrão: 16)
# Grava issues_piloto.json com título, rótulos, data, se é pull request, corpo e autor de cada issue.
# Usa a API pública do GitHub, sem chave (limite de 60 consultas por hora).
# Observação: o texto das issues pode ter sido editado depois de 07/11/2026; o arquivo issues_piloto.json
# guarda o texto como estava no piloto.
import json, sys, time, urllib.request

N = int(sys.argv[1]) if len(sys.argv) > 1 else 16
SLUG = {'nop': 'nopSolutions/nopCommerce', 'sharex': 'ShareX/ShareX'}
ordem = json.load(open('ordem_sorteio.json', encoding='utf-8'))
saida = {}
for r, slug in SLUG.items():
    for item in ordem[r][:N]:
        url = f"https://api.github.com/repos/{slug}/issues/{item['issue']}"
        req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'tcc-piloto'})
        d = json.load(urllib.request.urlopen(req, timeout=30))
        saida[f"{slug}:{item['issue']}"] = {'title': d['title'], 'labels': [l['name'] for l in d['labels']], 'created': d['created_at'],
                                           'pr': 'pull_request' in d, 'body': d.get('body') or '', 'user': d['user']['login']}
        print(r, item['issue'], saida[f"{slug}:{item['issue']}"]['labels'], d['title'][:60])
        time.sleep(1)
json.dump(saida, open('issues_piloto.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
