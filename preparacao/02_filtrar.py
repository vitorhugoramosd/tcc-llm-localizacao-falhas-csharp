# Etapa 1b: aplica os critérios de elegibilidade aos commits candidatos e grava elegiveis_pre.json.
# Uso: python 02_filtrar.py <pasta_dos_clones>   (rodar na pasta preparacao, depois do 01_candidatos.py)
# Critérios: a mensagem cita a issue; a issue tem um único commit; o commit não é junção de ramos (merge);
# e altera de 1 a 10 arquivos .cs que não são de teste.
import subprocess,re,sys,json,collections,os
CLONES = sys.argv[1] if len(sys.argv) > 1 else 'clones'
eh_teste=lambda p: re.search(r'(^|/)(tests?|[^/]*\.tests?)(/|$)|tests?\.cs$', p, re.I) is not None
out={}
for r in ['nop','sharex']:
    por_issue=collections.defaultdict(list)
    for l in open(f'cand_{r}.tsv',encoding='utf-8'):
        h,d,s=l.rstrip('\n').split('\t',2)
        if s.startswith('Merge'): continue
        m=re.match(r'^(?:fixed |fix(?:es)? )?#(\d+)',s,re.I) if r=='sharex' else re.match(r'^#(\d+)\b',s)
        if not m: continue
        por_issue[m.group(1)].append((h,d,s))
    res=[]
    for i,cs in por_issue.items():
        if len(cs)!=1: continue
        h,d,s=cs[0]
        if len(subprocess.check_output(['git','-C',os.path.join(CLONES,r),'rev-list','--parents','-n1',h]).split())!=2: continue
        fs=subprocess.check_output(['git','-C',os.path.join(CLONES,r),'diff-tree','--no-commit-id','--name-only','-r',h]).decode().split()
        cs_=[f for f in fs if f.endswith('.cs') and not eh_teste(f)]
        if 1<=len(cs_)<=10: res.append({'issue':int(i),'commit':h,'data':d,'msg':s,'n_cs':len(cs_)})
    out[r]=sorted(res,key=lambda x:x['issue'])
    print(r,len(por_issue),'issues ->',len(res),'com 1 commit e 1-10 .cs')
json.dump(out,open('elegiveis_pre.json','w',encoding='utf-8'),indent=1,ensure_ascii=False)
