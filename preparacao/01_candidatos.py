# Etapa 1a: lista os commits candidatos de cada repositório.
# Uso: python 01_candidatos.py <pasta_dos_clones>
# A pasta deve conter os clones "nop" (nopSolutions/nopCommerce) e "sharex" (ShareX/ShareX), no ramo develop.
# O período vai de 01/06/2024 até o momento em que o piloto foi preparado (07/11/2026, 15h UTC),
# e a data registrada é a do commit (committer date). Com esses limites, o resultado é idêntico ao do piloto.
import os, subprocess, sys

CLONES = sys.argv[1] if len(sys.argv) > 1 else 'clones'
for r in ('nop', 'sharex'):
    out = subprocess.check_output(['git', '-C', os.path.join(CLONES, r), 'log', '--since=2024-06-01', '--until=2026-11-07T15:00:00Z',
                                   '--date=short', '--format=%H%x09%cd%x09%s'], text=True, encoding='utf-8')
    with open(f'cand_{r}.tsv', 'w', encoding='utf-8', newline='\n') as f:
        f.write(out)
    print(r, len(out.splitlines()), 'commits candidatos')
