exec(open(r'work\spatial\scan.py').read().split('hits=[]')[0])
out=out/'render-source';r=0x7dac49;f=pe.function(r);rows=[pe.row(i) for i in pe.decode(f[0])];(out/'dispatcher-tailcaller.json').write_text(json.dumps({'function':hex(f[0]),'instructions':rows},indent=2));print('\n'.join(x['rva']+' '+x['text'] for x in rows))
