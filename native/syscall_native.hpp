// C++ / native/syscall_native.hpp / Windows x64
// Direct-syscall memory read path for the native panel. Replaces
// OpenProcess/ReadProcessMemory with raw NtOpenProcess/NtReadVirtualMemory so
// the panel bypasses kernel32 AND ntdll user-mode hooks. SSnumbers are
// resolved at runtime from the ntdll stubs, so it works across Windows builds.
#pragma once
#include <windows.h>
#include <cstdint>

namespace sc {

typedef LONG NTSTATUS;

inline DWORD resolve_ssn(const char* name) {
    HMODULE ntdll = GetModuleHandleA("ntdll.dll");
    if (!ntdll) return 0;
    BYTE* p = (BYTE*)GetProcAddress(ntdll, name);
    if (!p) return 0;
    for (int i = 0; i < 32; i++) {
        if (p[i] == 0x4C && p[i + 1] == 0x8B && p[i + 2] == 0xD1 && p[i + 3] == 0xB8)
            return *(DWORD*)(p + i + 4);
    }
    return 0;
}

typedef NTSTATUS (__stdcall* syscall5_fn)(uint64_t, uint64_t, uint64_t, uint64_t, uint64_t);

inline NTSTATUS raw_syscall(DWORD ssn, uint64_t a1, uint64_t a2, uint64_t a3, uint64_t a4, uint64_t a5) {
    static BYTE* stub = nullptr;
    static DWORD cur_ssn = 0;
    if (!stub) stub = (BYTE*)VirtualAlloc(nullptr, 32, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!stub) return (NTSTATUS)0xC0000001;
    if (cur_ssn != ssn) {
        stub[0] = 0x4C; stub[1] = 0x8B; stub[2] = 0xD1;   // mov r10, rcx
        stub[3] = 0xB8;                                    // mov eax, imm32
        *(DWORD*)(stub + 4) = ssn;
        stub[8] = 0x0F; stub[9] = 0x05;                    // syscall
        stub[10] = 0xC3;                                   // ret
        cur_ssn = ssn;
    }
    return ((syscall5_fn)stub)(a1, a2, a3, a4, a5);
}

inline HANDLE open_process(DWORD access, DWORD pid) {
    static DWORD ssn = 0;
    if (!ssn) ssn = resolve_ssn("NtOpenProcess");
    if (!ssn) return nullptr;
    struct { HANDLE UniqueProcess; HANDLE UniqueThread; } cid;
    cid.UniqueProcess = (HANDLE)(uintptr_t)pid;
    cid.UniqueThread = nullptr;
    struct { ULONG Length; HANDLE RootDirectory; void* ObjectName; ULONG Attributes;
             void* SecurityDescriptor; void* SecurityQualityOfService; } oa;
    oa.Length = sizeof(oa);
    oa.RootDirectory = nullptr;
    oa.ObjectName = nullptr;
    oa.Attributes = 0;
    oa.SecurityDescriptor = nullptr;
    oa.SecurityQualityOfService = nullptr;
    HANDLE h = nullptr;
    NTSTATUS st = raw_syscall(ssn, (uint64_t)&h, (uint64_t)access, (uint64_t)&oa, (uint64_t)&cid, 0);
    return st == 0 ? h : nullptr;
}

inline NTSTATUS read_mem(HANDLE h, uint64_t addr, void* buf, uint32_t size) {
    static DWORD ssn = 0;
    if (!ssn) ssn = resolve_ssn("NtReadVirtualMemory");
    if (!ssn) return (NTSTATUS)0xC0000001;
    ULONG bytes = 0;
    return raw_syscall(ssn, (uint64_t)h, addr, (uint64_t)buf, (uint64_t)size, (uint64_t)&bytes);
}

} // namespace sc
