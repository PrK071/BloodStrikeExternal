# Python | curate_audit_v2.py | Python 3.12+ and iced-x86 | Windows x64 static evidence classification.
import argparse
import hashlib
import json
from pathlib import Path
from audit_v2 import RawPE,PINNED,save


def main():
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--audit',type=Path,required=True)
    a=p.parse_args();pe=RawPE(a.binary)
    if pe.sha!=PINNED:raise ValueError('Different sample')
    functions=json.loads((a.audit/'functions.json').read_text())
    graphs=json.loads((a.audit/'reachable-code.json').read_text())
    instructions={int(r['rva'],16):r for f in functions+graphs for r in f['instructions']}
    claims=[]
    def add(id,status,claim,reason,addresses=(),sources=()):
        rows=[]
        for r in addresses:
            if r not in instructions:raise ValueError(f'Address not present in independently decoded regions: {r:x}')
            rows.append(instructions[r])
        claims.append(dict(id=id,status=status,claim=claim,reason=reason,sha256=pe.sha,evidence=rows,
                           public_sources=list(sources),runtime_validation=False))
    add('A01','CONFIRMADA','Os registros antigos de instrucoes, RVAs, xrefs e vftables sao estruturalmente consistentes.',
        'Segundo parser PE e iced-x86 conferem bytes, comprimento de instrucao e destinos; ver legacy-audit.json.')
    add('A02','PARCIAL','Reconstrucao do mapa de tipos e layouts a partir dos inventarios RTTI.',
        'A forma binaria e os nomes foram conferidos; faltam cobertura de tipos sem RTTI e tamanhos/semantica de campos.')
    add('A03','DESCARTADA','Uma entrada RUNTIME_FUNCTION ou truncated=false garante a funcao fonte completa.',
        'O ramo de sucesso do helper de listas sai do primeiro registro; o CFG alcanca quatro registros.',(0x2a8327c,0x2a83297))
    add('A04','DESCARTADA','Todos os enderecos do bloco asm do relatorio anterior estavam escritos como RVAs.',
        'As colunas da esquerda eram RVAs, enquanto destinos call absolutos foram formatados como VAs preferenciais.',(0x3239681,))
    add('A05','PARCIAL','Recuperacao das vftables, sua extensao e identidade dos metodos.',
        '132 ponteiros sao autenticos e tem relocacoes DIR64; extensao exata das tabelas e identidade dos metodos nao decorrem disso.')
    add('G01','CONFIRMADA','GetAllActors e registrado com callback no RVA 0x3259770.',
        'Nome e endereco sao escritos no mesmo registro de 32 bytes.',(0x3239686,0x3239693,0x3239696,0x323969d,0x32396a4,0x32396af))
    add('G02','CONFIRMADA','O registro integra a inicializacao do modulo de scripts MCharacter.',
        'A definicao de modulo aponta para MCharacter; a mesma rotina cria o modulo e instala o callback. Outra rotina usa o mesmo nome.',
        (0x32362e2,0x32362e9,0x323630e,0x3244dce),('https://docs.python.org/3.14/c-api/module.html#c.PyModuleDef',))
    add('G03','CONFIRMADA','A chamada de scripts nao aceita argumentos Python; o dispatcher fornece self e NULL conforme METH_NOARGS.',
        'Flag 4 seleciona o dispatcher NOARGS, que zera EDX antes da chamada indireta; isso nao equivale a prototipo C sem parametros.',
        (0x32396a4,0x2abf926,0x2abfe72,0x2abfe76,0x2abfe78),
        ('https://raw.githubusercontent.com/python/cpython/v3.14.0/Include/methodobject.h',
         'https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention?view=msvc-170'))
    add('G04','CONFIRMADA','O callback constroi uma lista Python nova e retorna a lista ou NULL nos caminhos observados.',
        'Alocacao com tamanho zero, PyTypeObject com nome list, append e fluxo de erro; ver script-bridge.json e reachable-code.json.',
        (0x3259786,0x3259788,0x2a832f5,0x2a832fc,0x2a832cf,0x2a832da,0x32597fe,0x3259837,0x325983f,0x3259843),
        ('https://raw.githubusercontent.com/python/cpython/v3.14.0/Objects/listobject.c',))
    add('G05','CONFIRMADA','O codigo demonstra a alocacao e inicializacao da raiz cujo ponteiro e armazenado em 0x8b7cd90.',
        'Alocacao de 0x40, inicializacao de sentinela e store global; o getter le esse slot. Valores vivos continuam desconhecidos.',
        (0x19b9366,0x19b937b,0x19b9385,0x19d45e0,0x1a52f8,0x1a52fb,0x1a52ff))
    add('G06','CONFIRMADA','Existe um caminho que associa um valor de 32 bits de Character::Actor a ActorComponent nesse registro.',
        'Construcao do ator, passagem ao componente, chave de quatro bytes e ponteiro this inserido no payload +0x18 do no.',
        (0x19bfe53,0x19bfe75,0x19c01dc,0x19c0266,0x19c03f0,0x19c03f7,0x19c03fd,0x19c0409,0x19c0410,0x254497,0x25449a,0x25449e))
    add('G07','PARCIAL','Caracterizacao dos elementos retornados como ActorComponent.',
        'O caminho de insercao acima e comprovado; nem todas as insercoes e subclasses dinamicas foram demonstradas.')
    add('G08','HIPÓTESE','GetAllActors enumera exclusivamente jogadores ou inimigos.',
        'Nao ha verificacao demonstrada de time, jogador local ou identidade de gameplay. O nome Actor nao prova isso.')
    add('G09','HIPÓTESE','O container tem exatamente a identidade fonte std::unordered_map<uint32_t, ActorComponent*>.',
        'Ha hashing de quatro bytes, buckets e nos encadeados. O nome/template e o sinal do tipo de chave nao foram recuperados.',
        (0x2543b8,0x2543d7,0x2543e3,0x2543ef,0x2543fe,0x254405,0x254497,0x25449e))
    add('G10','CONFIRMADA','O callback filtra por ponteiro nao nulo e mascara 0x10 em um objeto relacionado antes da conversao.',
        'Operacoes de leitura e teste sao explicitas; o significado de gameplay do bit nao foi identificado.',
        (0x32597c0,0x32597c4,0x32597c8,0x32597cd,0x32597dd))
    add('C01','CONFIRMADA','Character::Actor deriva de AnimationCore::Skeleton e instala sua vftable apos a inicializacao da base.',
        'RTTI, chamada da base e stores sucessivos de vptr.',(0x16d0e9a,0x115eb33,0x115eb3a,0x16d0e9f,0x16d0ea6))
    add('C02','CONFIRMADA','ActorComponent e SkeletonComponent possuem vptr principal +0 e subobjeto ITickable +0x68.',
        'Hierarquias RTTI, inicializadores de base/derivada e thunks de ajuste de this concordam.',
        (0x19bf534,0x19bf540,0x19bf54a,0xad5c24,0xad5c30,0xad5c3a,0xa03077,0xa03081,0x1a1e2fc,0x1a1e300,0xb1070c,0xb10710))
    add('C03','CONFIRMADA','ICamera deriva de IEntity e instala sua tabela principal em +0.',
        'RTTI e chamada do inicializador de IEntity, com stores da base e depois da derivada.',
        (0x275738,0x88ca40,0x88ca47,0x27573d,0x275744))
    add('C04','DESCARTADA','O offset +0x68 pode ser generalizado como vptr secundario das quatro classes.',
        'O subobjeto ITickable foi provado apenas nas duas classes de componentes; nao ha fundamento para a generalizacao.')
    add('C05','HIPÓTESE','ICamera +0x454 e necessariamente o FOV.',
        'A escrita dos bits de 60.0 e real; nome e unidade ainda nao foram demonstrados.',(0x27579c,))
    add('M01','CONFIRMADA','Ha procedencia embutida Python-3.14.0 nos helpers de listas usados pelo callback.',
        'As instrucoes de erro referenciam caminho PythonCore3/Python-3.14.0/Objects/listobject.c.',(0x2a83283,0x2a835a4))
    add('M02','PARCIAL','Identificacao do runtime incorporado com a base CPython 3.14.0.',
        'Nomes e operacoes concordam, mas caminhos nao comprovam identidade de fontes. Numeros de linha do binario diferem da tag publica.')
    add('M03','CONFIRMADA','Existem tipos C++ Asyncore::pybase_object_impl e Messiah::PythonAsyncoreModule.',
        'Nomes dos TypeDescriptors foram relidos e verificados independentemente; nao demonstram todas as regras de threading do framework.')
    add('M04','HIPÓTESE','A arquitetura inteira de scheduling, GIL e rede da engine pode ser deduzida desses wrappers.',
        'As evidencias analisadas cobrem registros, conversao e referencias; nao cobrem esses subsistemas por inteiro.')
    add('D01','DESCARTADA','O getter RVA 0x19d45e0 le o endereco externo 0x8a8e810.',
        'O destino RIP-relative e 0x8b7cd90 nesta amostra.',(0x19d45e0,))
    add('D02','DESCARTADA','O RVA da string GetAllActors pode ser usado como endereco da funcao.',
        'String em .rdata e callback em .text sao objetos distintos, associados por um registro.',(0x3239686,0x3239696))
    base_tables=[]
    for vt in (0x5325938,0x4f953e0,0x4f95470,0x4f2a180):
        col=pe.unpack('<Q',vt-8)[0]-pe.base
        sig,disp,cd,td,ch,selfr=pe.unpack('<6I',col)
        if sig!=1 or selfr!=col:raise ValueError('Invalid base initializer vftable metadata')
        base_tables.append(dict(vtable_rva=hex(vt),col_rva=hex(col),type_descriptor_rva=hex(td),
                                name=pe.string(td+16),subobject_offset=disp))
    save(a.audit/'base-initialization.json',base_tables)
    save(a.audit/'claims.json',claims)
    print(json.dumps(dict(claims=len(claims),statuses={s:sum(c['status']==s for c in claims) for s in ('CONFIRMADA','PARCIAL','HIPÓTESE','DESCARTADA')}),ensure_ascii=True))


if __name__=='__main__':main()
