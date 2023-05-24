from pwn import ELF

from commons import binary


def test_mitigations() -> None:
    elf = ELF("others/essay-checker.elf", checksec=False)
    found_mitigations = list(binary.get_mitigations(elf))
    assert found_mitigations == [binary.Mitigation.RELRO]


def test_context() -> None:
    elf = ELF("others/essay-checker.elf", checksec=False)
    context = list(binary.get_context_aspects(elf))
    assert context == [
        binary.ContextAspects.EXECSTACK,
        binary.ContextAspects.RWX_SEGMENTS,
    ]


def test_sensitive_functions() -> None:
    elf = ELF("others/cookie_lover.elf", checksec=False)
    sensitives = list(binary.get_sensitive_functions_addresses(elf))
    assert sensitives == ["send_flag"]
