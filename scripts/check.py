"""Run the same suites as CTest, including in toolchains without ctest."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
from build_config import cmake_cache

root = Path(__file__).resolve().parent.parent

def python_timeout(value):
    try:
        seconds = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Python suite timeout requires an integer in 1..86400") from error
    if not 1 <= seconds <= 86400:
        raise argparse.ArgumentTypeError("Python suite timeout requires an integer in 1..86400")
    return seconds

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--build", type=Path, default=root / "build")
parser.add_argument("--python-timeout", type=python_timeout, default=600,
                    help="finite wall deadline for the complete Python suite in seconds (1..86400; default 600)")
args = parser.parse_args()
cache=cmake_cache(args.build,os.environ.get("PCE_TEST_CMAKE_CACHE"))
desktop_enabled=cache is not None and "PCE_BUILD_DESKTOP:BOOL=ON" in cache.read_text(encoding="utf-8").splitlines()
environment=os.environ.copy()
if cache is not None:
    environment["PCE_TEST_CMAKE_CACHE"]=str(cache)
environment["PCE_TEST_DESKTOP"]=str(args.build.resolve()/("pce-desktop.exe" if os.name=="nt" else "pce-desktop")) if desktop_enabled else "disabled"
environment["PCE_TEST_HEADLESS"]=str(args.build.resolve() / ("pce-headless.exe" if os.name=="nt" else "pce-headless"))
environment["SDL_AUDIODRIVER"]="dummy"
subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], cwd=root, env=environment, check=True, timeout=args.python_timeout)
subprocess.run([str(args.build.resolve() / ("pce-native-dispatch-tests.exe" if os.name=="nt" else "pce-native-dispatch-tests"))],cwd=root,check=True,timeout=60)
for suite in ("pce-reset-tests", "pce-hucard-tests", "pce-mapper-tests", "pce-arcade-tests", "pce-mirror-tests", "pce-brk-tests", "pce-context-tests", "pce-speed-trace-tests", "pce-cd-decode-tests", "pce-sprite-tests", "pce-vram-latch-tests", "pce-vdc-queue-tests", "pce-timer-tests", "pce-code-capture-tests"):
    subprocess.run([str(args.build.resolve() / (suite+(".exe" if os.name=="nt" else "")))],cwd=root,check=True,timeout=60)
binary = args.build.resolve() / ("pce-runtime-tests.exe" if os.name == "nt" else "pce-runtime-tests")
subprocess.run([str(binary)], cwd=root, check=True, timeout=60)
io_binary=args.build.resolve() / ("pce-io-tests.exe" if os.name=="nt" else "pce-io-tests")
subprocess.run([str(io_binary)], cwd=root, check=True, timeout=60)
vdc_binary=args.build.resolve() / ("pce-vdc-tests.exe" if os.name=="nt" else "pce-vdc-tests")
subprocess.run([str(vdc_binary)], cwd=root, check=True, timeout=60)
raster_binary=args.build.resolve() / ("pce-raster-tests.exe" if os.name=="nt" else "pce-raster-tests")
subprocess.run([str(raster_binary)], cwd=root, check=True, timeout=60)
scsi_binary=args.build.resolve() / ("pce-scsi-tests.exe" if os.name=="nt" else "pce-scsi-tests")
subprocess.run([str(scsi_binary)], cwd=root, check=True, timeout=60)
subprocess.run([str(args.build.resolve() / ("pce-cd-unknown-tests.exe" if os.name=="nt" else "pce-cd-unknown-tests"))],cwd=root,check=True,timeout=60)
subprocess.run([str(args.build.resolve() / ("pce-cd-timing-tests.exe" if os.name=="nt" else "pce-cd-timing-tests"))],cwd=root,check=True,timeout=60)
subprocess.run([str(args.build.resolve() / ("pce-cd-timing-checkpoint-tests.exe" if os.name=="nt" else "pce-cd-timing-checkpoint-tests"))],cwd=root,check=True,timeout=60)
joypad_binary=args.build.resolve() / ("pce-joypad-tests.exe" if os.name=="nt" else "pce-joypad-tests")
subprocess.run([str(joypad_binary)], cwd=root, check=True, timeout=60)

for suite in ("pce-read-tests", "pce-sense-tests", "pce-cue-tests", "pce-cue-gap-tests", "pce-sector-tests", "pce-subchannel-sector-tests", "pce-subchannel-tests", "pce-cd-position-tests"):
    command=[str(args.build.resolve() / (suite + (".exe" if os.name=="nt" else "")))]
    if suite in ("pce-sector-tests", "pce-subchannel-sector-tests", "pce-cd-position-tests"):
        extension=".dll" if os.name=="nt" else (".so")
        prefix=""
        if sys.platform=="darwin": extension=".so"
        command.append(str(args.build.resolve() / (prefix+"pce-sector-decoder-fixture"+extension)))
    subprocess.run(command,cwd=root,check=True,timeout=60)

subprocess.run([str(args.build.resolve() / ("pce-block-tests.exe" if os.name=="nt" else "pce-block-tests"))],cwd=root,check=True,timeout=60)

subprocess.run([str(args.build.resolve() / ("pce-irq-tests.exe" if os.name=="nt" else "pce-irq-tests"))],cwd=root,check=True,timeout=60)
subprocess.run([str(args.build.resolve() / ("pce-irq-boundary-tests.exe" if os.name=="nt" else "pce-irq-boundary-tests"))],cwd=root,check=True,timeout=60)
subprocess.run([str(args.build.resolve() / ("pce-irq-device-tests.exe" if os.name=="nt" else "pce-irq-device-tests"))],cwd=root,check=True,timeout=60)
subprocess.run([str(args.build.resolve() / ("pce-irq-stall-tests.exe" if os.name=="nt" else "pce-irq-stall-tests"))],cwd=root,check=True,timeout=60)
subprocess.run([str(args.build.resolve() / ("pce-vram-active-tests.exe" if os.name=="nt" else "pce-vram-active-tests"))],cwd=root,check=True,timeout=60)
subprocess.run([str(args.build.resolve() / ("pce-vdc-scroll-tests.exe" if os.name=="nt" else "pce-vdc-scroll-tests"))],cwd=root,check=True,timeout=60)

subprocess.run([str(args.build.resolve() / ("pce-video-tests.exe" if os.name=="nt" else "pce-video-tests"))],cwd=root,check=True,timeout=60)

for suite in ("pce-audio-tests","pce-dma-tests","pce-psg-pcm-tests","pce-adpcm-pcm-tests","pce-pcm-output-tests","pce-cdda-stream-tests","pce-audio-dsp-tests","pce-audio-timing-tests","pce-cdda-latch-tests"):
    subprocess.run([str(args.build.resolve() / (suite+(".exe" if os.name=="nt" else "")))],cwd=root,check=True,timeout=60)

subprocess.run([str(args.build.resolve() / ("pce-adpcm-tests.exe" if os.name=="nt" else "pce-adpcm-tests"))],cwd=root,check=True,timeout=60)

subprocess.run([str(args.build.resolve() / ("pce-cdda-tests.exe" if os.name=="nt" else "pce-cdda-tests"))],cwd=root,check=True,timeout=60)
subprocess.run([str(args.build.resolve() / ("pce-cdda-pcm-tests.exe" if os.name=="nt" else "pce-cdda-pcm-tests")),
                str(args.build.resolve() / ("pce-sector-decoder-fixture.dll" if os.name=="nt" else "pce-sector-decoder-fixture.so"))],cwd=root,check=True,timeout=60)

subprocess.run([str(args.build.resolve() / ("pce-input-script-tests.exe" if os.name=="nt" else "pce-input-script-tests"))],cwd=root,check=True,timeout=60)

subprocess.run([str(args.build.resolve() / ("pce-scanline-tests.exe" if os.name=="nt" else "pce-scanline-tests"))],cwd=root,check=True,timeout=60)
desktop_tests=args.build.resolve() / ("pce-desktop-tests.exe" if os.name=="nt" else "pce-desktop-tests")
if desktop_enabled:
    desktop_env=os.environ.copy()
    desktop_env.update(SDL_VIDEODRIVER="dummy",SDL_RENDER_DRIVER="software",SDL_AUDIODRIVER="dummy")
    subprocess.run([str(desktop_tests)],cwd=root,env=desktop_env,check=True,timeout=60)
    subprocess.run([str(args.build.resolve() / ("pce-audio-host-tests.exe" if os.name=="nt" else "pce-audio-host-tests"))],cwd=root,env=desktop_env,check=True,timeout=60)

subprocess.run([str(args.build.resolve() / ("pce-dev-server-tests.exe" if os.name=="nt" else "pce-dev-server-tests"))],cwd=root,check=True,timeout=60)
subprocess.run([str(args.build.resolve() / ("pce-adpcm-irq-tests.exe" if os.name=="nt" else "pce-adpcm-irq-tests"))],cwd=root,check=True,timeout=60)
for suite in ("pce-checkpoint-tests","pce-checkpoint-audio-tests","pce-cd-read-checkpoint-tests","pce-cd-adpcm-checkpoint-tests","pce-dma-irq-checkpoint-tests","pce-block-dma-irq-checkpoint-tests","pce-vdc-adpcm-irq-checkpoint-tests","pce-cdda-gap-tests","pce-cdda-end-tests","pce-psg-phase-tests","pce-psg-pipeline-tests","pce-vdc-latch-checkpoint-tests"):
    subprocess.run([str(args.build.resolve() / (suite+(".exe" if os.name=="nt" else "")))],cwd=root,check=True,timeout=60)

subprocess.run([sys.executable, str(root/'tests/test_psg_pipeline_fixture.py'), '--fresh',
                str(args.build.resolve()/('pce-psg-pipeline-tests.exe' if os.name=='nt' else 'pce-psg-pipeline-tests'))],
               cwd=root, check=True, timeout=60)
