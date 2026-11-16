# -*- coding: utf-8 -*-
"""Piloto do TCC (localização de falhas com LLMs em C#). Usa só a biblioteca padrão do Python 3.

Modos:
  python piloto.py api <rotulo> <modelo>     consultas automáticas por API compatível com OpenAI (padrão: OpenRouter)
  python piloto.py chat <rotulo>             roteiro manual para usar a interface de chat (copia o prompt e recebe a resposta)
  python piloto.py resultados                calcula Top-1, Top-3, Top-5 e MRR e grava resultados.csv

Exemplos:
  set OPENROUTER_API_KEY=sk-or-...
  python piloto.py api llama meta-llama/llama-3.3-70b-instruct:free
  python piloto.py chat claude

  Gemini pela API gratuita do Google AI Studio:
  set PILOTO_URL=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
  set PILOTO_CHAVE=<chave do AI Studio>
  python piloto.py api gemini gemini-2.5-flash
"""
import json, os, sys, time, re, urllib.request, urllib.error, datetime, subprocess, csv

AQUI = os.path.dirname(os.path.abspath(__file__))
DEF = json.load(open(os.path.join(AQUI, 'defeitos.json'), encoding='utf-8'))
INSTR_MET = json.load(open(os.path.join(AQUI, 'modelo_consulta_metodo.json'), encoding='utf-8'))['instrucao_metodo']
URL_API = os.environ.get('PILOTO_URL', 'https://openrouter.ai/api/v1/chat/completions')
CHAVE = os.environ.get('PILOTO_CHAVE') or os.environ.get('OPENROUTER_API_KEY', '')
MAX_TOKENS = int(os.environ.get('PILOTO_MAX_TOKENS', '8000'))


def ler(nome):
    return open(os.path.join(AQUI, 'consultas', nome), encoding='utf-8').read()


def extrair_json(txt):
    """Pega o primeiro objeto JSON da resposta (aceita bloco ```json ... ```)."""
    txt = re.sub(r'<(think|thought)>.*?</(think|thought)>', '', txt or '', flags=re.S)  # remove o raciocínio que alguns modelos devolvem
    m = re.search(r'\{.*\}', txt, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


_ARQS = {}
def arquivos_repo(d):
    """Lista de arquivos .cs do commit pai, lida da própria consulta de arquivo."""
    if d['id'] not in _ARQS:
        lista, pasta = [], ''
        for l in ler(f"{d['id']}_1_arquivo.txt").split('### Source files', 1)[1].splitlines()[1:]:
            if l.endswith('/') and not l.startswith(' '): pasta = l
            elif l.startswith('  ') and l.strip(): lista.append(pasta + l.strip())
        _ARQS[d['id']] = lista
    return _ARQS[d['id']]


def resolver(d, caminho):
    """Caminho exato; se o modelo encurtou o caminho, aceita quando ele é o final de um único arquivo do repositório."""
    c = (caminho or '').replace('\\', '/').strip()
    while c.startswith('./'): c = c[2:]
    c = c.lstrip('/')
    arqs = arquivos_repo(d)
    if c in arqs: return c
    cand = [a for a in arqs if a.lower().endswith('/' + c.lower())]
    return cand[0] if len(cand) == 1 else c


def baixar_arquivo(d, caminho):
    url = f"https://raw.githubusercontent.com/{d['repositorio']}/{d['commit_pai']}/{resolver(d, caminho)}"
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'tcc-piloto'}), timeout=30).read().decode('utf-8', 'replace')
    except urllib.error.HTTPError:
        return None


def consulta_metodo(d, arquivos):
    nome = d['repositorio'].split('/')[1]
    relato = ler(f"{d['id']}_3_memorizacao.txt").split('### Bug report', 1)[1].strip()
    partes, usados = [], []
    for c in (arquivos or [])[:5]:
        src = baixar_arquivo(d, c)
        if src is not None:
            c = resolver(d, c); usados.append(c)
            partes.append(f"### File: {c}\n```csharp\n{src}\n```")
    if not partes:
        return None, []
    return INSTR_MET.format(repo=nome) + f"\n\n### Bug report\n{relato}\n\n" + '\n\n'.join(partes) + '\n', usados


def chamar_api(modelo, prompt):
    corpo = {'model': modelo, 'temperature': 0, 'max_tokens': MAX_TOKENS,
             'messages': [{'role': 'user', 'content': prompt}]}
    if os.environ.get('PILOTO_SEM_TEMPERATURA'):
        corpo.pop('temperature')  # modelos que não aceitam temperatura (ex.: Claude 5.5 pela API)
    if 'openrouter' in URL_API:
        corpo['usage'] = {'include': True}  # OpenRouter devolve o custo junto com os tokens
    req = urllib.request.Request(URL_API, data=json.dumps(corpo).encode('utf-8'),
                                 headers={'Authorization': f'Bearer {CHAVE}', 'Content-Type': 'application/json'})
    t0 = time.time()
    for tentativa in range(4):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=180))
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (429, 500, 503) and tentativa < 3:  # limite de requisições ou servidor sobrecarregado: espera e tenta de novo
                print(f'   HTTP {e.code}, aguardando 60 s... {msg[:160]}'); time.sleep(60); continue
            return {'erro': f'HTTP {e.code}: {msg}', 'segundos': round(time.time() - t0, 1)}
        except Exception as e:  # tempo esgotado ou falha de conexão: tenta de novo
            if tentativa < 3:
                print(f'   {type(e).__name__}, tentando de novo...'); continue
            return {'erro': str(e), 'segundos': round(time.time() - t0, 1)}
    else:
        return {'erro': 'limite de requisições', 'segundos': round(time.time() - t0, 1)}
    if 'choices' not in r:
        return {'erro': json.dumps(r)[:300], 'segundos': round(time.time() - t0, 1)}
    u = r.get('usage', {}) or {}
    return {'texto': r['choices'][0]['message'].get('content') or '', 'modelo_resposta': r.get('model'),
            'tokens_entrada': u.get('prompt_tokens'), 'tokens_saida': u.get('completion_tokens'), 'tokens_total': u.get('total_tokens'),
            'custo_usd': u.get('cost'), 'segundos': round(time.time() - t0, 1)}


def consultar_com_repeticao(modelo, prompt, chave_json):
    """Uma resposta fora do formato leva a uma nova consulta; se falhar de novo, conta como não localizado."""
    regs = []
    for _ in range(2):
        r = chamar_api(modelo, prompt); regs.append(r)
        j = extrair_json(r.get('texto'))
        if j and chave_json in j:
            return j, regs
    return None, regs


def salvar(rotulo, d, dados):
    pasta = os.path.join(AQUI, 'respostas', rotulo); os.makedirs(pasta, exist_ok=True)
    json.dump(dados, open(os.path.join(pasta, f"{d['id']}.json"), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


def modo_api(rotulo, modelo):
    if not CHAVE:
        sys.exit('Defina a chave: set OPENROUTER_API_KEY=... (ou PILOTO_CHAVE e PILOTO_URL para outro provedor)')
    pasta = os.path.join(AQUI, 'respostas', rotulo); os.makedirs(pasta, exist_ok=True)
    for d in DEF:
        if os.path.exists(os.path.join(pasta, f"{d['id']}.json")):
            print(d['id'], 'já feito, pulando'); continue
        parc = os.path.join(pasta, f"{d['id']}.parcial")  # guarda cada consulta já feita, para retomar sem repetir
        res = json.load(open(parc, encoding='utf-8')) if os.path.exists(parc) else \
            {'id': d['id'], 'rotulo': rotulo, 'modelo_pedido': modelo, 'meio': 'API', 'data': datetime.datetime.now().isoformat(timespec='seconds')}
        grava = lambda: json.dump(res, open(parc, 'w', encoding='utf-8'), ensure_ascii=False)
        if 'arquivos' not in res:
            print(d['id'], '-> consulta de arquivo')
            j1, res['reg_arquivo'] = consultar_com_repeticao(modelo, ler(f"{d['id']}_1_arquivo.txt"), 'files')
            res['arquivos'] = (j1 or {}).get('files', []); grava()
        if 'metodos' not in res:
            p2, res['arquivos_lidos'] = consulta_metodo(d, res['arquivos'])
            if p2:
                print(d['id'], '-> consulta de método')
                j2, res['reg_metodo'] = consultar_com_repeticao(modelo, p2, 'methods')
                res['metodos'] = (j2 or {}).get('methods', [])
            else:
                res['metodos'], res['reg_metodo'] = [], []
            grava()
        if 'memorizacao' not in res:
            print(d['id'], '-> teste de memorização')
            j3, res['reg_memorizacao'] = consultar_com_repeticao(modelo, ler(f"{d['id']}_3_memorizacao.txt"), 'file')
            res['memorizacao'] = (j3 or {}).get('file')
        salvar(rotulo, d, res)
        if os.path.exists(parc):
            try: os.remove(parc)
            except OSError: os.replace(parc, parc + '.ok')
    print('Pronto. Agora rode: python piloto.py resultados')


def copiar(texto):
    try:
        subprocess.run(['clip'], input=texto.encode('utf-16le'), check=True)  # Windows
        return True
    except Exception:
        return False


def receber_json(chave_json):
    print(f'   Cole a resposta do chat aqui (o JSON com "{chave_json}") e tecle Enter. Se o chat falhou, digite FALHOU.')
    linhas = []
    while True:
        l = input()
        if l.strip().upper() == 'FALHOU':
            return None, '\n'.join(linhas)
        linhas.append(l)
        j = extrair_json('\n'.join(linhas))
        if j and chave_json in j:
            return j, '\n'.join(linhas)


def passo_chat(nome, prompt, chave_json):
    caminho = os.path.join(AQUI, 'colar_no_chat.txt')
    open(caminho, 'w', encoding='utf-8').write(prompt)
    ok = copiar(prompt)
    print(f"\n== {nome}: prompt de {len(prompt):,} caracteres " + ('COPIADO para a área de transferência.' if ok else f'salvo em {caminho}.'))
    print('   Abra um chat NOVO (temporário/anônimo, sem busca na web), cole com Ctrl+V e envie.')
    t0 = time.time()
    j, bruto = receber_json(chave_json)
    return j, {'texto': bruto, 'segundos_ate_colar': round(time.time() - t0, 1)}


def modo_chat(rotulo):
    modelo = input('Qual modelo a interface mostra (ex.: GPT-5.x, Claude Sonnet 5.5)? ').strip()
    for d in DEF:
        if os.path.exists(os.path.join(AQUI, 'respostas', rotulo, f"{d['id']}.json")):
            print(d['id'], 'já feito, pulando'); continue
        print(f"\n######## Defeito {d['id']} ({d['url']})")
        res = {'id': d['id'], 'rotulo': rotulo, 'modelo_pedido': modelo, 'meio': 'chat', 'data': datetime.datetime.now().isoformat(timespec='seconds')}
        j1, r1 = passo_chat('Consulta 1 (arquivo)', ler(f"{d['id']}_1_arquivo.txt"), 'files')
        res['reg_arquivo'] = [r1]; res['arquivos'] = (j1 or {}).get('files', [])
        p2, res['arquivos_lidos'] = consulta_metodo(d, res['arquivos'])
        if p2:
            j2, r2 = passo_chat('Consulta 2 (método)', p2, 'methods')
            res['reg_metodo'] = [r2]; res['metodos'] = (j2 or {}).get('methods', [])
        else:
            print('   Nenhum dos arquivos indicados existe no repositório: consulta de método não localizada.')
            res['reg_metodo'] = []; res['metodos'] = []
        j3, r3 = passo_chat('Consulta 3 (memorização)', ler(f"{d['id']}_3_memorizacao.txt"), 'file')
        res['reg_memorizacao'] = [r3]; res['memorizacao'] = (j3 or {}).get('file')
        salvar(rotulo, d, res)
        print(f"   {d['id']} salvo.")
    print('\nPronto. Agora rode: python piloto.py resultados')


norm = lambda p: (p or '').replace('\\', '/').strip().lstrip('./').lower()
base = lambda p: norm(p).rsplit('/', 1)[-1]


def posicao_arquivo(d, lista):
    alvo = {norm(a) for a in d['referencia']['arquivos']}
    for i, a in enumerate(lista[:5], 1):
        if norm(resolver(d, a)) in alvo:
            return i
    return None


def posicao_metodo(d, lista):
    alvo = {(base(m['arquivo']), m['metodo'].lower()) for m in d['referencia']['metodos']}
    for i, m in enumerate(lista[:5], 1):
        if isinstance(m, dict):
            nome = str(m.get('method', '')).split('(')[0].split('.')[-1].strip().lower()
            if (base(resolver(d, m.get('file', ''))), nome) in alvo:
                return i
    return None


def modo_resultados():
    linhas = []
    pasta = os.path.join(AQUI, 'respostas')
    for rotulo in sorted(os.listdir(pasta)) if os.path.isdir(pasta) else []:
        for d in DEF:
            f = os.path.join(pasta, rotulo, f"{d['id']}.json")
            if not os.path.exists(f):
                continue
            r = json.load(open(f, encoding='utf-8'))
            regs = r.get('reg_arquivo', []) + r.get('reg_metodo', []) + r.get('reg_memorizacao', [])
            soma = lambda k: sum((x.get(k) or 0) for x in regs)
            linhas.append({'rotulo': rotulo, 'meio': r.get('meio'), 'defeito': d['id'], 'perfil': d['perfil'],
                           'pos_arquivo': posicao_arquivo(d, r.get('arquivos', [])),
                           'pos_metodo': posicao_metodo(d, r.get('metodos', [])),
                           'memorizacao_acertou': norm(resolver(d, r.get('memorizacao'))) in {norm(a) for a in d['referencia']['arquivos']},
                           'consultas': len(regs), 'tokens_entrada': soma('tokens_entrada'), 'tokens_saida': soma('tokens_saida'), 'tokens_total': soma('tokens_total'),
                           'custo_usd': round(soma('custo_usd'), 6), 'segundos': round(soma('segundos') + soma('segundos_ate_colar'), 1)})
    if not linhas:
        sys.exit('Nenhuma resposta encontrada em respostas/.')
    with open(os.path.join(AQUI, 'resultados.csv'), 'w', newline='', encoding='utf-8') as fp:
        w = csv.DictWriter(fp, fieldnames=list(linhas[0]), delimiter=';'); w.writeheader(); w.writerows(linhas)
    print(f"{'rótulo':10} {'perfil':22} {'nível':8} {'n':>2} {'Top-1':>6} {'Top-3':>6} {'Top-5':>6} {'MRR':>5}")
    for rotulo in sorted({l['rotulo'] for l in linhas}):
        for perfil in sorted({l['perfil'] for l in linhas}):
            g = [l for l in linhas if l['rotulo'] == rotulo and l['perfil'] == perfil]
            for nivel in ('arquivo', 'metodo'):
                ps = [l[f'pos_{nivel}'] for l in g]
                if not ps: continue
                top = lambda n: 100 * sum(1 for p in ps if p and p <= n) / len(ps)
                mrr = sum(1 / p for p in ps if p) / len(ps)
                print(f"{rotulo:10} {perfil:22} {nivel:8} {len(ps):>2} {top(1):6.0f} {top(3):6.0f} {top(5):6.0f} {mrr:5.2f}")
    print('\nDetalhes por defeito em resultados.csv')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['api'] and len(a) == 3: modo_api(a[1], a[2])
    elif a[:1] == ['chat'] and len(a) == 2: modo_chat(a[1])
    elif a[:1] == ['resultados']: modo_resultados()
    else: print(__doc__)
