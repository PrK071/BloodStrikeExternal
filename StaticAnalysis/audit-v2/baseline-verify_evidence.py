# Python | verify_evidence.py | Python 3.12+ | Windows x64; independently verify static evidence.
"""Check generated RVAs against raw file bytes and a second PE mapper, then curate facts."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).parent.parent))
from inspect_build import PortableExecutable

PINNED_SHA256="ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary",type=Path,required=True)
    parser.add_argument("--results",type=Path,required=True)
    args=parser.parse_args()
    data=args.binary.read_bytes(); digest=hashlib.sha256(data).hexdigest()
    pe=PortableExecutable(data)
    def load(name):return json.loads((args.results/name).read_text(encoding="utf8"))
    summary=load("summary.json")
    if summary["sha256"]!=digest:raise ValueError("Report refers to different binary")
    for field,value in (("image_base_preferred",pe.image_base),("size_of_image",pe.image_size),("entry_point_rva",pe.entry_point)):
        if int(summary[field],16)!=value:raise ValueError("Independent PE parser mismatch: "+field)
    if int(summary["pe_timestamp_raw"],16)!=pe.timestamp:raise ValueError("PE timestamp mismatch")
    instruction_count=0
    for function in load("function-evidence.json"):
        for ins in function["instructions"]:
            rva=int(ins["rva"],16); off=pe.rva_to_offset(rva); expected=bytes.fromhex(ins["bytes"])
            if off!=int(ins["file_offset"],16) or data[off:off+len(expected)]!=expected:
                raise ValueError("Instruction bytes mismatch at "+ins["rva"])
            instruction_count+=1
    refs=load("code-xrefs.json")
    for ref in refs:
        rva=int(ref["instruction_rva"],16); off=pe.rva_to_offset(rva)
        # This validator does not use Capstone or the primary analyzer's RVA mapper.
        decoded_target=rva+7+struct.unpack_from("<i",data,off+3)[0]
        if decoded_target!=int(ref["target_rva"],16):raise ValueError("RIP-relative mismatch")
    slots=0
    for table in load("core-vtables.json"):
        for slot in table["entries"]:
            off=pe.rva_to_offset(int(slot["slot_rva"],16))
            if struct.unpack_from("<Q",data,off)[0]-pe.image_base!=int(slot["function_rva"],16):
                raise ValueError("Vtable pointer mismatch")
            slots+=1
    result=dict(generated_utc=datetime.now(timezone.utc).isoformat(),sha256=digest,
                independent_pe_parser="inspect_build.PortableExecutable (no pefile dependency)",
                matched_instructions=instruction_count,matched_rip_xrefs=len(refs),matched_vtable_slots=slots,
                status="PASS",runtime_validation=False,
                meaning="File consistency and address arithmetic validated; object behavior was not executed")
    (args.results/"verification.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    if digest!=PINNED_SHA256:
        raise ValueError("Generic verification passed, but curated findings are pinned to another SHA256")
    packets=[]
    def packet(identifier,claim,expected,confidence="ALTA",semantic_limit=None):
        evidence=[]
        for rva,raw,comment in expected:
            off=pe.rva_to_offset(rva); needle=bytes.fromhex(raw)
            if off is None or data[off:off+len(needle)]!=needle:
                raise ValueError(f"Curated evidence mismatch: {identifier} {rva:x}")
            evidence.append(dict(rva=hex(rva),preferred_va=hex(pe.image_base+rva),file_offset=hex(off),
                                 bytes=needle.hex(" "),interpretation=comment))
        packets.append(dict(id=identifier,claim=claim,status="CONFIRMADO_NO_BINARIO",confidence=confidence,
                            evidence=evidence,semantic_limit=semantic_limit))
    packet("getallactors-binding","O nome GetAllActors e o callback RVA 0x3259770 sao associados no mesmo registro.",[
        (0x3239686,"48 8d 15 eb f1 97 02","LEA da string RVA 0x5bb8878"),
        (0x3239693,"48 89 10","Grava ponteiro do nome em registro +0"),
        (0x3239696,"48 8d 15 d3 00 02 00","LEA do callback RVA 0x3259770"),
        (0x323969d,"48 89 50 08","Grava callback em registro +8"),
        (0x32396a4,"c7 40 10 04 00 00 00","Grava flags 4 em registro +0x10"),
        (0x32396ab,"48 89 70 18","Grava ponteiro em registro +0x18"),
        (0x32396af,"e8 bc 61 9c fe","Passa registro a rotina RVA 0x1bff870")],
        semantic_limit="Registro compativel com PyMethodDef x64; nao e endereco de lista de jogadores.")
    packet("binding-record-size","O registro acima recebe alocacao solicitada de 0x20 bytes.",[
        (0x3239679,"b9 20 00 00 00","ECX = 0x20 antes da chamada de alocacao"),
        (0x3239681,"e8 e2 2a 01 01","CALL RVA 0x424c168")])
    packet("enumeration-global","O callback chama um getter que le um ponteiro no RVA 0x8b7cd90.",[
        (0x32597a5,"e8 36 ae 77 fe","CALL RVA 0x19d45e0"),
        (0x19d45e0,"48 8b 05 a9 87 1a 07 c3","MOV RAX,[RIP+0x71a87a9]; RET => RVA 0x8b7cd90")],
        semantic_limit="Uso como raiz de enumeracao comprovado. Nome da classe, vida util e conteudo runtime nao confirmados.")
    packet("enumeration-observed-accesses","A enumeracao usa estes deslocamentos e um teste de bit.",[
        (0x32597aa,"48 8b 78 08","Le ponteiro de [resultado_getter+8]"),
        (0x32597ae,"48 8b 1f","Le primeiro ponteiro do objeto anterior"),
        (0x32597c0,"48 8b 53 18","Le [no_atual+0x18]"),
        (0x32597c4,"48 8b 42 40","Le [valor_anterior+0x40]"),
        (0x32597cd,"f6 80 30 01 00 00 10","Testa bit 0x10 no byte +0x130 do objeto nao nulo"),
        (0x325982f,"48 8b 1b","Avanca via [no_atual+0]")],
        semantic_limit="Layout operacional parcial sem nomes de campos; tipo STL, identidade de jogador e semantica do bit nao comprovados.")
    packet("actor-vptr","Inicializacao de Character::Actor instala a vftable em +0.",[
        (0x16d0e94,"48 8b f9","RDI preserva RCX, ponteiro de instancia"),
        (0x16d0e9f,"48 8d 05 ba 41 e9 03","Carrega vftable RVA 0x5565060"),
        (0x16d0ea6,"48 89 07","Instala vptr em [RDI+0]")])
    packet("actorcomponent-vptrs","ActorComponent instala vptrs em +0 e +0x68; RTTI confirma subobjeto ITickable em +0x68.",[
        (0x19bf52a,"48 8b d9","RBX preserva RCX"),
        (0x19bf539,"48 8d 05 b8 c3 bd 03","Vftable primaria RVA 0x559b8f8"),
        (0x19bf540,"48 89 03","Store em +0"),
        (0x19bf543,"48 8d 05 a6 c4 bd 03","Vftable secundaria RVA 0x559b9f0"),
        (0x19bf54a,"48 89 43 68","Store em +0x68")])
    packet("skeletoncomponent-vptrs","SkeletonComponent instala vptrs em +0 e +0x68.",[
        (0xad5c1a,"48 8b d9","RBX preserva RCX"),
        (0xad5c29,"48 8d 05 70 c6 4c 04","Vftable primaria RVA 0x4fa22a0"),
        (0xad5c30,"48 89 03","Store em +0"),
        (0xad5c33,"48 8d 05 56 c7 4c 04","Vftable secundaria RVA 0x4fa2390"),
        (0xad5c3a,"48 89 43 68","Store em +0x68")])
    packet("camera-initialization","ICamera instala vptr em +0 e inicializa armazenamento em +0x408 e +0x454.",[
        (0x27572b,"48 8b f9","RDI preserva RCX"),
        (0x27573d,"48 8d 05 14 1e be 04","Vftable RVA 0x4e57558"),
        (0x275744,"48 89 07","Store vptr em +0"),
        (0x275747,"c7 87 08 04 00 00 01 00 01 00","Dword +0x408 = 0x10001"),
        (0x27579c,"c7 87 54 04 00 00 00 00 70 42","Dword +0x454 = 0x42700000 (60.0 se interpretado como float)")],
        semantic_limit="O nome FieldOfView para +0x454 nao esta comprovado; nao e publicado como offset de FOV.")
    packet("camera-reflection-delegation","Wrappers associados a ViewMatrix e FieldOfView usam ajuste e chamada indireta.",[
        (0x93f1a4,"48 63 0d 8d 5f 60 04","Le ajuste em RVA 0x4f45138"),
        (0x93f1ae,"48 8b 05 7b 5f 60 04","Le delegado em RVA 0x4f45130"),
        (0x943d44,"48 63 0d 25 78 60 04","Le ajuste em RVA 0x4f4b570"),
        (0x943d4e,"48 8b 05 13 78 60 04","Le delegado em RVA 0x4f4b568")],
        semantic_limit="Ponteiros e ajustes sao zero no arquivo; nao derivam layout final de matriz/FOV nesta etapa.")
    (args.results/"confirmed-evidence.json").write_text(json.dumps(packets,indent=2,ensure_ascii=True)+"\n",encoding="utf8")
    print(json.dumps(dict(**result,curated_packets=len(packets))))


if __name__=="__main__":main()
