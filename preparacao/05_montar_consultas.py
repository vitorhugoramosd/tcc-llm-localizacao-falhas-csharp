# Etapas 1 a 3 do piloto: registra os defeitos, extrai a referência de acerto e monta as consultas.
# Uso: python 05_montar_consultas.py <pasta_dos_clones> [pasta_de_saida]   (rodar na pasta preparacao)
# Grava defeitos.json, modelo_consulta_metodo.json e consultas/ na pasta de saída (padrão: ../piloto).
# Precisa das bibliotecas tree-sitter e tree-sitter-c-sharp (ver requirements.txt).
import subprocess, re, json, os, collections, sys
from tree_sitter import Language, Parser
import tree_sitter_c_sharp as tcs

CLONES = sys.argv[1] if len(sys.argv) > 1 else 'clones'
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join('..', 'piloto')
REPOS = {'nop': ('nopSolutions/nopCommerce', 'nopCommerce', 'com testes'),
         'sharex': ('ShareX/ShareX', 'ShareX', 'legado (sem testes)')}
# defeitos sorteados (semente 20261107) que passaram nos critérios + caso do teste preliminar #8369 (ver conferencia_issues.md)
DEFEITOS = [('nop', 8299), ('nop', 8409), ('nop', 7587), ('sharex', 8568), ('sharex', 8699), ('sharex', 8091), ('nop', 8369)]

eh_teste = lambda p: re.search(r'(^|/)(tests?|[^/]*\.tests?)(/|$)|tests?\.cs$', p, re.I) is not None
parser = Parser(Language(tcs.language()))
git = lambda r, *a: subprocess.check_output(['git', '-C', os.path.join(CLONES, r), *a]).decode('utf-8', 'replace')
issues = json.load(open('issues_piloto.json', encoding='utf-8'))
eleg = json.load(open('elegiveis_pre.json', encoding='utf-8'))


def metodos(src):
    t = parser.parse(src); res = []
    def walk(n, cls):
        if n.type in ('class_declaration', 'interface_declaration', 'struct_declaration', 'record_declaration'):
            nm = n.child_by_field_name('name'); cls = nm.text.decode() if nm else cls
        if n.type in ('method_declaration', 'constructor_declaration', 'property_declaration', 'local_function_statement', 'operator_declaration'):
            nm = n.child_by_field_name('name')
            nome = nm.text.decode() if nm else n.type
            res.append((cls, nome, n.start_point[0] + 1, n.end_point[0] + 1))
        for c in n.children: walk(c, cls)
    walk(t.root_node, None); return res


def linhas_pai(r, pai, fix, p):
    d = git(r, 'diff', '-w', '-U0', pai, fix, '--', p); ls = set()  # -w: ignora mudanças só de espaço
    for m in re.finditer(r'^@@ -(\d+)(?:,(\d+))? \+', d, re.M):
        ini = int(m.group(1)); n = int(m.group(2) or 1)
        ls.update(range(ini, ini + n) if n > 0 else [ini])
    return ls


def arvore(paths):
    # lista agrupada por pasta: reduz o tamanho da consulta sem perder nenhum caminho
    g = collections.OrderedDict()
    for p in paths:
        d, f = p.rsplit('/', 1) if '/' in p else ('.', p)
        g.setdefault(d, []).append(f)
    return '\n'.join(f'{d}/\n' + '\n'.join('  ' + f for f in fs) for d, fs in g.items())


os.makedirs(f'{OUT}/consultas', exist_ok=True)
lista = []
for r, n in DEFEITOS:
    slug, nome, perfil = REPOS[r]
    iss = issues.get(f'{slug}:{n}')
    if n == 8369:
        txt = open('issue_8369.md', encoding='utf-8').read().strip()  # issue usada no teste preliminar (texto guardado)
        fix = '32f317901f2cf5467755abf604e8289483ba51da'; criado = '2026-10-15'
    else:
        txt = f"Title: {iss['title']}\n\n{iss['body'].strip()}"; criado = iss['created'][:10]
        fix = [e['commit'] for e in eleg[r] if e['issue'] == n][0]
    pai = git(r, 'rev-parse', fix + '^').strip()
    alt = [p for p in git(r, 'diff', '--name-only', pai, fix).split() if p.endswith('.cs') and not eh_teste(p)]
    alt = [p for p in alt if git(r, 'diff', '-w', '-U0', pai, fix, '--', p).count('\n@@') or git(r, 'diff', '-w', '-U0', pai, fix, '--', p).startswith('@@')]
    ref_met = []
    for p in alt:
        try: src = git(r, 'show', f'{pai}:{p}').encode()
        except subprocess.CalledProcessError: continue  # arquivo novo
        ls = linhas_pai(r, pai, fix, p)
        if not ls: continue
        for cls, nm, a, b in metodos(src):
            if any(a <= l <= b for l in ls):
                ref_met.append({'arquivo': p, 'classe': cls, 'metodo': nm, 'linhas': [a, b]})
    # remove métodos externos que só contêm o método interno alterado (função local) - mantém todos, critério: contém linha alterada
    cs = sorted(p for p in git(r, 'ls-tree', '-r', '--name-only', pai).split('\n') if p.endswith('.cs') and not eh_teste(p))
    base = lambda p: os.path.basename(p)[:-3]
    alvos = set(base(p) for p in alt) | set(m['metodo'] for m in ref_met) | set(m['classe'] or '' for m in ref_met)
    pistas = sorted(a for a in alvos if a and len(a) > 3 and re.search(r'\b' + re.escape(a) + r'\b', txt))
    did = f'{r}-{n}'
    c1 = (f"You are helping to locate a bug in the C# repository {nome}. Below is the bug report and the list of all .cs source files "
          "in the repository, grouped by folder (full path = folder + file name). Return the 5 files most likely to contain the code that "
          "must be changed to fix the bug, ordered from most to least likely. Do not search the web. "
          'Answer ONLY with JSON in the format {"files": ["full/path1.cs", "full/path2.cs", "full/path3.cs", "full/path4.cs", "full/path5.cs"]}.'
          f"\n\n### Bug report\n{txt}\n\n### Source files ({len(cs)})\n{arvore(cs)}\n")
    c3 = (f"Below is a bug report from the C# repository {nome} (github.com/{slug}). You will not receive any list of files or code. "
          "Give the exact path of the .cs file that was changed to fix this bug. Do not search the web. "
          'Answer ONLY with JSON in the format {"file": "path"}.'
          f"\n\n### Bug report\n{txt}\n")
    open(f'{OUT}/consultas/{did}_1_arquivo.txt', 'w', encoding='utf-8').write(c1)
    open(f'{OUT}/consultas/{did}_3_memorizacao.txt', 'w', encoding='utf-8').write(c3)
    item = {'id': did, 'repositorio': slug, 'perfil': perfil, 'issue': n, 'url': f'https://github.com/{slug}/issues/{n}',
            'criada_em': criado, 'commit_correcao': fix, 'commit_pai': pai, 'arquivos_cs_no_repositorio': len(cs),
            'referencia': {'arquivos': alt, 'metodos': ref_met}, 'relato_cita_alvo': pistas,
            'tamanho_consulta_arquivo_chars': len(c1), 'tokens_estimados_consulta_arquivo': round(len(c1) / 3.6)}
    lista.append(item)
    print(did, criado, 'arqs', len(alt), 'mets', len(ref_met), 'pistas', pistas, 'c1', len(c1), '~tok', item['tokens_estimados_consulta_arquivo'])

json.dump(lista, open(f'{OUT}/defeitos.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
# texto da consulta 2 (método): o script do Windows completa com o conteúdo dos 5 arquivos escolhidos
json.dump({'instrucao_metodo': (
    "You are helping to locate a bug in the C# repository {repo}. Below is the bug report and the full content of 5 source files. "
    "Return the 5 methods most likely to contain the code that must be changed to fix the bug, ordered from most to least likely. "
    "Do not search the web. Answer ONLY with JSON in the format "
    '{{"methods": [{{"file": "full/path.cs", "method": "MethodName"}}, ...]}} with exactly 5 items.')},
    open(f'{OUT}/modelo_consulta_metodo.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
