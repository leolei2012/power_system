"""Render the two current Rev E PCB review boards without changing their sources.

Run with the workspace Python (PyMuPDF is used to rasterize native KiCad SVG).
These are review images, not fabrication or assembly outputs.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
CLI = Path('C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
BOARDS = {
    'controller': ROOT / 'controller/hardware/g431_core/controller.kicad_pcb',
    'inverter': ROOT / 'inverter/hardware/inverter.kicad_pcb',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(job):
    name, args = job
    process = subprocess.run([str(CLI)] + [str(x) for x in args], capture_output=True,
                             text=True, encoding='utf-8', errors='replace', timeout=180,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    if process.returncode:
        raise RuntimeError((name, process.returncode, process.stdout, process.stderr))
    return {'name': name, 'command': [str(CLI)] + [str(x) for x in args],
            'stdout': process.stdout.strip(), 'stderr': process.stderr.strip()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'outputs/pcb_review_2026-11-11/previews')
    parser.add_argument('--only', choices=list(BOARDS))
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    selected = {name: path for name, path in BOARDS.items() if not args.only or name == args.only}
    before = {name: digest(path) for name, path in selected.items()}
    jobs = []
    for name, board in selected.items():
        for side in ('top', 'bottom'):
            prefix = 'F' if side == 'top' else 'B'
            cmd = ['pcb', 'export', 'svg', '--mode-single', '--fit-page-to-board',
                   '--exclude-drawing-sheet', '--layers',
                   f'{prefix}.Cu,{prefix}.SilkS,{prefix}.Fab,Edge.Cuts',
                   '--output', output / f'{name}_{side}.svg']
            if side == 'bottom':
                cmd.append('--mirror')
            jobs.append((name + '_' + side, cmd + [board]))
        jobs.append((name + '_3d', ['pcb', 'render', '--width', '1400', '--height', '1050',
                    '--side', 'top', '--quality', 'basic', '--background', 'opaque',
                    '--rotate', '330,0,20', '--zoom', '0.65' if name == 'inverter' else '0.9', '--output',
                    output / f'{name}_3d.png', board]))
    records = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(run, job): job[0] for job in jobs}
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            print('Exported ' + record['name'], flush=True)
    for name in selected:
        for side in ('top', 'bottom'):
            svg = output / f'{name}_{side}.svg'
            # KiCad's pale silk color is intended for a dark editor canvas.
            # Keep the native SVG and geometry; darken ink for the white-paper PNG.
            paper_svg = svg.read_text(encoding='utf-8').replace('#F2EDA1', '#1F2937')
            with fitz.open(stream=paper_svg.encode('utf-8'), filetype='svg') as source:
                pdf = source.convert_to_pdf()
            with fitz.open(stream=pdf, filetype='pdf') as doc:
                page = doc[0]
                scale = 1600 / max(page.rect.width, page.rect.height)
                page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).save(
                    str(output / f'{name}_{side}.png'))
    assert before == {name: digest(path) for name, path in selected.items()}, 'PCB changed while exporting'
    manifest = {'revision': 'E-PCB-0.1-review', 'source_pcb_sha256': before,
                'scope': 'Native KiCad layout and 3D review images; not fabrication outputs.',
                'PNG_palette_note': 'Pale native silkscreen ink is darkened on the white-paper 2D PNG; geometry is unchanged. Native SVG is preserved.',
                'exports': records,
                'image_sha256': {f'{name}_{side}.png': digest(output / f'{name}_{side}.png')
                                  for name in selected for side in ('top', 'bottom', '3d')}}
    filename = 'preview_manifest.json' if not args.only else args.only + '_preview_manifest.json'
    (output / filename).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': 'PASS', 'boards': list(selected), 'output': str(output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
