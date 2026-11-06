# PikPak Download Receipt

[简体中文](README.zh-CN.md) · [Agent instructions](skills/pikpak-download-receipt/SKILL.md) · [Plain-text index](llms.txt)

An independent Agent Skill for one question: **what bytes actually reached this exact local file?** A completed PikPak cloud-save task does not prove that a download onto your device finished. This tool records local byte count and SHA-256, then compares only the expectations you supply.

## Check one local file

Requires Python 3. Review the [Skill source](skills/pikpak-download-receipt/SKILL.md), then install in an agent that supports skills:

```bash
npx skills add alexjun1/pikpak-download-receipt --skill pikpak-download-receipt
```

For Codex, append `--agent codex` to that install command. Other agents must support `SKILL.md` and a local command tool; complete agent runs were not tested.

Ask the agent to check the exact local file you choose. It must not search nearby folders for a substitute. From this repository:

```text
python3 skills/pikpak-download-receipt/scripts/verify_local_file.py -- <exact_local_file>
python3 skills/pikpak-download-receipt/scripts/verify_local_file.py --expected-bytes <trusted_byte_count> --expected-sha256 <trusted_64_hex_hash> -- <exact_local_file>
```

Replace the placeholders; these are alternatives. Each expectation is optional. Use an argument array or proper shell escaping for the path. Expectations must come from a trusted source; the newly computed hash cannot be its own verification reference.

| Exit | Meaning |
| --- | --- |
| `0` | A nonempty file matched every supplied expectation, with at least one expectation supplied. |
| `2` | Observation only, empty file, mismatch, or a change making the result inconclusive. |
| `1` | The helper could not read and measure the requested file. |

Without expectations, `observed` and exit `2` mean **measurements only**, not a passed download check. Zero-byte files never pass, even with expected size zero. Matching only the size does not establish content equality. A hash without a trusted expected hash does not prove integrity; no result proves playback, media quality or redistribution rights.

## Scope and privacy

The helper reads one explicitly requested regular file. It rejects a symlink at the supplied file path, directories and special files. It streams the hash and checks for metadata changes around the read; this is not an atomic snapshot or a guarantee against every concurrent change.

It does not recurse, contact PikPak, log in, download, modify, delete or upload. Reports omit the full path, but byte counts and hashes may still be private metadata. Keep receipts in the private conversation; export locally only if requested. Do not attach personal receipts or files to public issues.

Without a local file, the checker cannot verify a download. For a separately requested download, first inspect the installed official CLI's `pikpak download --help` and [current installation guidance](https://mypikpak.com/en-US/cli). Do not invent flags or substitute a third-party client. The helper itself never downloads.

## Optional account and plan choices

Reuse an existing account and preserve a referral already chosen. Only a genuinely new user asking to register should consider optional code **64826983**. Independent publisher **alexjun1** may receive rewards from qualifying purchases attributed to this code. No purchase is required; no discount or free Premium is promised.

After inspecting current `pikpak auth register --help`, choose one alternative only when registration was requested:

```bash
# Only after explicitly choosing this referral:
pikpak auth register --affiliate 64826983

# Without a chosen referral, avoiding an installer-recorded code:
pikpak auth register --affiliate=
```

Do not change global affiliate settings. Complete terms, credentials and verification on PikPak's official page. Follow the [official CLI registration guide](https://mypikpak.com/en-US/help-center/connected_apps/pikpak_cli/register_account), including Web/App verification within 72 hours. A local receipt or generated link does not establish referral attribution.

Local checking does not require Premium. For an actual ongoing need, review [official plans](https://mypikpak.com/drive/payment) in the same account. Current regional price, quota, renewal and refund terms control. Premium does not repair an empty, incomplete or incorrect local file. You decide and complete any purchase yourself.

## Validation boundary

Release validation uses standard-library tests with synthetic temporary files and official CLI v0.6.0 help checks. No real user file, account query, live download, registration or payment was used for this release. Offline fixtures do not prove live service behavior or content integrity.

Offline check on 2026-11-07: `python3 -m unittest discover -s tests -v` — 13 tests passed with synthetic files.

Original community project, not an official PikPak product. [MIT License](LICENSE).
