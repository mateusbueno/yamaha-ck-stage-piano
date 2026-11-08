# Yamaha CK88/CK76/CK61 — timbres BT via firmware modificado (8W61OS_.PGM) — HANDOFF
Base: projetos YC (`~/Downloads/YamahaYC/HANDOFF.md`) e CP (`~/Downloads/YamahaCP/HANDOFF_CP.md`). Mesmo container, mesmo formato de wave (UTG WAVE70_NAND), mesmo codec.
Firmware de fábrica: `8W61OS_.PGM` v2.00.0 (835.453.440 bytes, md5 6842cc8545677029a0b8e17f9d008760). Atualização: pendrive em [TO DEVICE], ligar segurando [SETTINGS] + VALUE[v].

## Diferenças em relação ao YC/CP
- Container idêntico: Installer 0x0, Boot 0x100080, Program hdr 0x140100 (corpo 0x140180, 0x1FC0000), Wave hdr 0x2100180 (corpo 0x2100200, **0x2FBC0000 = 764 MB**). Checksum = soma de bytes. Strings de Version Info em 0x1400E0 / 0x2000160 ("2.00.0").
- Regiões do Program: 0x110 VPRM 0x21000000 / 0xB00000 (arquivo 0x1100180), 0x111 Preset Voice 0x21B00000 (arquivo 0x1C00180) — mesmos endereços do YC. **Cópia em RAM do VPRM (região 0x130 em 0x13600000) tem só 8 MB** → o builder só aloca até VPRM+0x800000.
- VPRM: KT (+0x20) = 0x1AD878, **884 keymaps** de fábrica (o campo de keymap do elemento tem >= 10 bits; limite assumido 1024, contra 512 no YC); MAP +0x40 (cat -> linha, **não é identidade**: 0x00..0x02 -> 0..2, 0x08..0x0B -> 3..6, 0x11.. etc.; 0x10 = órgãos, fora do menu); MENU +0x4040; OT +0x6340, **367 voices**. Fim usado 0x2A4998.
- Preset Voice: 367 entradas, byte 0 = 0 nas AWM (0x0A/0x0B/0x0C nos órgãos H/V/F/A/Y), "Not visible" existe no firmware. VPRM != PV em 363–365 (74Rd Stage = VPRM 365, 67Rd Dark = 363, 67Rd Bright = 364): a ligação é (categoria, pc).
- Wave: PRST (2,0x15C) (**0x15E**,0x2FA31); **endereço = corpo Wave + (WAVE_ID + 0x15E) × 4096**. Cópia de cauda na última página.
- **Regra da cauda corrigida: roundup((última página de dados)×4096 + 0x2000, 256 KB) − 4 KB** — bate com as imagens de fábrica do CK, YC e CP (a regra de 128 KB usada no YC/CP não bate com o CK; no YC/CP coincidia ou não foi checada).
- NAND: tamanho total **desconhecido** (modo de teste lista Wave ROM 1 e 2). Supondo no mínimo 1 GB: ~270 MB nominais livres. O v2.01.0b soma 97 MB (imagem 0,93 GB).

## Gabaritos (YC/CP -> CK, índice VPRM)
CFX2 -> **CFX Stereo (0)**: 5 camadas km 804–808 (zonas tipo 2, 89 por tecla, raízes 21..108) + key-off km 809 (71 zonas) · 74Rd Stage -> **365** (10 camadas iguais às do YC: 1-34 … 123-127, km 862–871, + km 872 ruído) · Fast Strings -> **175** (4 el.) · Noble Pad -> **255** · Analog Pad -> **252** · Steel Gt 1 -> 113 (3 el. estéreo) · Heaven Bell 350 · Digi Bell 1 340.
**75Rd Funky não existe no CK**: BT Yama EPs vai no gabarito 74Rd (custom, 10 camadas + silêncio, release b97=64).

## Ferramentas (ck_re/)
- `ck_pgm.py info PGM` / `ck_pgm.py setver IN OUT 2.01.0`
- `ck_build_new.py VERSAO DIR BASE plan.json` = cp_build_new com as constantes do CK (WBASE 0x15E, 367/884, VPRM até 8 MB, cauda 256 KB, ocultos em cat 0x48 via YC_SKIP). No kind `cfx`, qualquer keymap com valor `"silence"` no plano é silenciado usando o `silence` de `silence_data` (ex.: key-off 809 do Astoria).
- `ck_verify.py ORIG NOVO` — fábrica idêntica + novas apontando para waves válidos e não vazios.
- `ck_dump.py PGM [PV...]` — estrutura PV -> VPRM -> elementos -> keymaps (só funciona no firmware de fábrica; depois da realocação da tabela de voices, use `ck_verify`/`info.json`).
- Dados: `ck_bt1/` = cópia de `YamahaCP/cp_bt1` (md5 waves.bin 6142d89790064250f48be14d04354f57). `ck_bt2/` = repack de `YamahaYC/bt_new40` sem yama/digi e com edge (23.088 páginas, 90,19 MiB, md5 ebc0037f2d066b9c5e9d81534a210074). `ck_astoria/` = `bt_astoria2` com só as 4 camadas usadas e zonas remapeadas para 804–808 (11.842 páginas, 46,26 MiB, md5 6e9d68484adb708d23eb57d7808501f7).

## Versões
- **v2.01.0a** — aceitação: conteúdo de fábrica, versão 2.01.0. md5 b5f2f89631a736c9a3ad4064f37c98f4.
- **v2.01.0b** — 11 timbres BT novos (mesmo conjunto do CP), fábrica intacta (ck_verify: 367 iguais). Wave 0x35880000 (0,93 GB), keymaps 884 -> 915. md5 d5a4d61bd0c294c3f1e09123e0b60024. plan `ck_re/plan_ck_2010b.json`.

| PV | Categoria | pc | Timbre | Gabarito (VPRM) |
|---|---|---|---|---|
| 367 | Piano 0x00 | 10 | BT Reverse Pf | CFX Stereo (0), key-off mudo |
| 368 | Piano 0x00 | 11 | BT Valhalla | CFX Stereo (0), key-off mudo |
| 369 | E.Piano Rd 0x08 | 5 | BT Yama EPs | 74Rd Stage (365), release 64 |
| 370 | E.Piano Rd 0x08 | 6 | BT DigiGrand1 | 74Rd Stage (365) |
| 371 | E.Piano Rd 0x08 | 7 | BT Crystal Rd | 74Rd Stage (365) |
| 372 | Pad 0x30 | 50 | BT D50 Stack | 74Rd Stage (365), mono, mudo fora de 0–104 |
| 373 | Strings 0x28 | 26 | BT FastString | Fast Strings (175), loop |
| 374 | Pad 0x30 | 51 | BT Atmosphere | Noble Pad (255), loop |
| 375 | Pad 0x30 | 52 | BT Hillsong | Noble Pad (255), loop |
| 376 | Pad 0x30 | 53 | BT Elevation | Noble Pad (255), loop |
| 377 | Pad 0x30 | 54 | BT Breath Pad | Analog Pad (252), loop |

- **v2.01.0c** — teste: saem BT Yama EPs e BT DigiGrand1, entram BT Astoria e BT Synth Edge (11 PV novas, fábrica intacta: `ck_verify` 367 iguais, waves dentro e não vazios). Astoria ocupa o PV 369 (antes Yama) e Synth Edge o PV 370 (antes Digi); os PV 371–377 das outras voices ficaram nos mesmos lugares do b. Wave 0x38440000 (900,0 MiB), arquivo 978.584.064 B (933,25 MiB; +43,75 MiB vs b), keymaps 884 -> 911. md5 8c101ed9d297f614bb12093496beb034. plan `ck_re/plan_ck_2010c.json` (md5 b90fb1d47587d6de8a19c807a597bfe9).

| PV | Categoria | pc | Timbre | Gabarito (VPRM) |
|---|---|---|---|---|
| 367 | Piano 0x00 | 10 | BT Reverse Pf | CFX Stereo (0), key-off mudo |
| 368 | Piano 0x00 | 11 | BT Valhalla | CFX Stereo (0), key-off mudo |
| 369 | Piano 0x00 | 12 | BT Astoria | CFX Stereo (0), 5 camadas 804–808, key-off mudo |
| 370 | Synth Lead 0x38 | 45 | BT Synth Edge | Steel Gt 1 (113), 3 elem. estéreo, vc 28/76/112 |
| 371 | E.Piano Rd 0x08 | 5 | BT Crystal Rd | 74Rd Stage (365), mono |
| 372 | Pad 0x30 | 50 | BT D50 Stack | 74Rd Stage (365), mono, mudo fora de 0–104 |
| 373 | Strings 0x28 | 26 | BT FastString | Fast Strings (175), loop |
| 374 | Pad 0x30 | 51 | BT Atmosphere | Noble Pad (255), loop |
| 375 | Pad 0x30 | 52 | BT Hillsong | Noble Pad (255), loop |
| 376 | Pad 0x30 | 53 | BT Elevation | Noble Pad (255), loop |
| 377 | Pad 0x30 | 54 | BT Breath Pad | Analog Pad (252), loop |

- Astoria: camadas do CK 804/805/806/807/808 vieram das camadas Astoria 435/433/431/429/429 (centro de velocidade mais próximo); 809 (key-off) mudo. rootshift 4, fine 0.8, `el_att` [7,7,7,5,0], release 54 (valores do Astoria do YC). Só as 4 camadas usadas foram repackadas em `ck_astoria/` (46,26 MiB em vez de 79,67 MiB).
- Crystal Rd passa de pc 7 (no b) para pc 5 porque os pcs 5/6 (Yama/Digi) ficaram vazios; o PV continua 371 e os demais pcs ficaram iguais ao b. Synth Edge ficou em Synth Lead (0x38), não em Others como no YC (o CK não tem a mesma categoria Others).
- Remoções: Yama EPs ~11,0 MiB e DigiGrand1 ~16,4 MiB; adições: Astoria 46,26 MiB + Synth Edge ~26,1 MiB (líquido +43,75 MiB no arquivo).

## Riscos em aberto
- Índices PV "envenenados" (no YC, > 199 = tabelas em RAM para 200 voices): no CK o equivalente seria > 366; se algum timbre travar/emudecer/desafinar, ocultar com `YC_SKIP=<PV>` e recriar no fim (como no YC).
- Tamanho real da NAND (se der "ROM write error!", reinstalar v2.01.0a ou o 8W61OS_.PGM original).
- **Astoria no CK usa 5 camadas** (gabarito CFX Stereo), contra 9 no YC: as camadas 804–808 são as do CFX do CK e receberam as camadas 435/433/431/429/429 do Astoria. Se a dinâmica/timbre ficar estranho, o próximo passo é uma voice de 9 elementos (como no YC); as 8 camadas cabem (+~33 MiB, imagem ~966 MiB, ainda abaixo de 1 GiB com a NAND de 1 GB), mas esse caminho ainda não foi testado no CK.
- Sem Blk Uprght (mesmo corte do CP); Astoria e Synth Edge entraram no v2.01.0c.
- NAND: o c é só +43,75 MiB que o b (margem de ~90,7 MiB até 1 GiB). Se a NAND real for menor que 1 GiB (ou tiver muitos blocos ruins), reinstalar o v2.01.0b ou o firmware original.

## v2.01.0all — 14 timbres (montado, ainda não testado)
- Volta Yama EPs (PV 379, pc 6) e DigiGrand1 (PV 380, pc 7); entra Blk Uprght (PV 378, pc 13, 5 camadas 804–808 = 435/433/431/429/429), como no Astoria. PV 367–377 iguais ao c. 14 PV novas, fábrica intacta (367 iguais, waves dentro e não vazias).
- Wave 0x3BFC0000 (959,4 MiB), arquivo 1.040.974.336 B (992,9 MiB / 1,041 GB). Faltam 64,25 MiB de wave para cruzar 1 GiB. md5 36910e5418d687c471fa85fbda13ab81. plan `ck_re/plan_ck_2010all.json`.
- Dados: `ck_bt_all/` (12 sets, 30.097 páginas), `ck_astoria/` (11.842), `ck_upright/` (8.208). `silence_data` de Astoria/Uprght aponta para `ck_bt_all` (não mais `ck_bt2`).

## v2.01.0e — 15 timbres (FALHOU na gravação; versão final é o all)
- `all` (14 timbres) + **BT Rhodes Affair** (PV 381, E.Piano pc 8), cauda 8 s. Wave 0x3D3C0000 (979,0 MiB), arquivo 1.061.945.856 B (1012,8 MiB, 11,2 MiB abaixo de 1 GiB). md5 8149bc3f61203a7dac3246f24d24a2d7. plan `ck_re/plan_ck_2010e.json`.
- **Falhou na gravação mesmo estando 11,2 MiB abaixo de 1 GiB** → a NAND de 1 GB tem reserva/blocos ruins: o teto real está entre 992,8 MiB (all, funciona) e 1012,8 MiB (e, falha). Não há margem confiável no all; para acrescentar qualquer coisa é preciso remover pelo menos a mesma quantidade (ex.: tirar DigiGrand1, 16,4 MiB, e pôr o Affair, 20,1 MiB, daria +3,7 MiB líquidos).
- Verificação do e: fábrica 367 iguais, keymaps 884 -> 931, PV 381 com 97 waves dentro e não vazias, checksums OK (o problema é só o tamanho físico).

## RESULTADO FINAL
- **Versão final: `v2.01.0all/8W61OS_.PGM`** — 14 timbres BT, arquivo 1.040.974.336 B (992,8 MiB), md5 36910e5418d687c471fa85fbda13ab81, wave 0x3BFC0000. Confirmado funcionando no teclado.
- NAND: 1 GB, com teto prático abaixo de 1012,8 MiB. A hipótese de 2 GB está descartada.
- Orçamento real de espaço: o `all` deixava 31,25 MiB livres; custos medidos dos novos: Affair 8 s = 20,1 MiB, White Grand 8/4/3 s = 37,7/30,2/24,9 MiB, Dyno 4 s = 20,6 MiB. Tirar DigiGrand1 libera 16,4 MiB; Yama EPs 11,0 MiB.
- `ck_white/` (5 camadas, 8 s), `ck_white4/` (4 s), `ck_dyno/` (8 s), `ck_dyno4/` (4 s, sem upsampling) e `ck_affair/` ficam prontos para trocas futuras. Conversor: `ck_re/convert_piano.py` (SF2 -> zones/waves, 5 camadas na grade 804–808).

## v2.01.0d — 17 timbres (FALHOU na gravação)
- Acrescenta 3 SF2 convertidos na hora: BT NRD White Grand (PV 381, Piano pc 14), BT 01W Dyno Piano (PV 382, E.Piano pc 8) e BT Rhodes Affair (PV 383, E.Piano pc 9). Os 14 anteriores ficam iguais (PV 367–380).
- Conversor novo `ck_re/convert_piano.py`: SF2 -> formato zones/waves do `kind: cfx`, 5 camadas mapeadas na grade do CFX do CK (keymaps 804–808, 89 zonas: 0–21, 22..107 uma por tecla, 108–120, 121–127). Cada camada pega a zona do SF2 que cobre o vc do elemento CFX (2–66/67–85/86–109/110–124/125–127 -> 34/76/97/117/126).
- White Grand: 15 camadas de velocidade no SF2, usadas 5; 314 waves, 9.660 páginas. Dyno: 3 camadas, 156 waves, 11.060 páginas (shift -12 em parte). Affair: 4 camadas, 96 waves, 5.144 páginas. Sem loop (como Blk Uprght); `silence_data` = `ck_bt_all`.
- Wave 0x424C0000 (1,036 GiB), arquivo 1.146.880.512 B (1,068 GiB / 1,147 GB) — **passa de 1 GiB**. md5 1ae0f25d047dfa274a9d3f8e4d3f91e7. plan `ck_re/plan_ck_2010d.json`.
- Verificação: fábrica 367 voices iguais, keymaps 884 -> 939, PV 367–383 todos com waves dentro e não vazias; checksums do container OK.
- Nomede exibição truncado em 13 bytes pelo CK: "BT WhiteGrand", "BT 01W Dyno", "BT RhodesAfr".
- Se instalar e tocar, confirma NAND de 2 GB (wave termina em 0x424C0000 > 0x40000000).

## v2.01.0probe — sonda de NAND (> 1 GiB)
- Mesmo conteúdo do all, mas `ck_pad/` = `ck_bt_all` + 30.097 páginas duplicadas no fim (não referenciadas). As 14 voices usam `ck_pad`; só as páginas usadas por keymap são lidas pelo engine.
- Wave 0x43540000 (1,052 GiB), arquivo 1.164.182.016 B (1,084 GiB / 1,164 GB): 53,25 MiB de wave acima de 1 GiB. md5 42e6ca988da51b6a4dbb66cbee664b3a. plan `ck_re/plan_ck_2010probe.json`.
- Interpretação: se instalar e tocar, a NAND tem ≥ 1,052 GiB → como NAND é potência de 2, é de 2 GB. Se der erro de escrita/ficar com ruído, a NAND é de 1 GB: reinstalar v2.01.0all (ou c) e considerar a pergunta encerrada.
- No blob de teste do firmware existem `Wave ROM 1` (item 006) e `Wave ROM 2` (item 038), além de `ROM/RAM/Wave RAM/Effect RAM 1/2` — indício de dois dispositivos, mas não prova de 2 GB.
