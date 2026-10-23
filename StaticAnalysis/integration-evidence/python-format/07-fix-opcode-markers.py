from pathlib import Path
p=Path(r'C:\Users\luiz\Documents\BloodStrikeExternal\StaticAnalysis\integration-evidence\python-format')
for name in ['03-static-marshal.py','05-opcodes-selected.py']:
 f=p/name;s=f.read_text();s=s.replace('ops={int(n):name for name,n in re.findall(', 'ops={int(n):name for name,n in re.findall(')
 # Both comprehensions have same final regex mode, one with optext, one inline.
 if name.startswith('03'):
  old="optext,re.M)}";new="optext,re.M) if name not in {'HAVE_ARGUMENT','MIN_SPECIALIZED_OPCODE','MIN_INSTRUMENTED_OPCODE'}}"
 else:
  old=".read_text(),re.M)}";new=".read_text(),re.M) if name not in {'HAVE_ARGUMENT','MIN_SPECIALIZED_OPCODE','MIN_INSTRUMENTED_OPCODE'}}"
 assert old in s;s=s.replace(old,new,1)
 if name.startswith('05'):
  marker="initial=json.loads((OUT/'marshal-static-results.json').read_text());summary=[]";assert marker in s
  head,body=s.split(marker,1);s=head+'def main():\n'+''.join(' '+line+'\n' for line in (marker+body).splitlines())+"\nif __name__=='__main__':main()\n"
 f.write_text(s)
f=p/'06-parser-checks.py';s=f.read_text();marker="(OUT/'parser-negative-tests.json').write_text";i=s.index(marker)
s=s[:i]+"decoder=runpy.run_path(str(OUT/'05-opcodes-selected.py'))\nassert decoder['ops'][43]=='WITH_EXCEPT_START'\nassert decoder['ops'][129]=='BINARY_OP_ADD_FLOAT'\nassert decoder['ops'][234]=='INSTRUMENTED_END_FOR'\nassert decoder['instructions']([{'opcode':43,'arg_byte':0}])[0]['opname']=='WITH_EXCEPT_START'\ntests.append({'test':'opcode_markers_excluded_43_129_234','status':'PASS'})\n"+s[i:];f.write_text(s)
