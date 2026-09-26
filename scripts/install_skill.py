"""Install the complete skill without modifying any existing installation."""
import argparse
import os
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dest', help='Skill parent directory; defaults to CODEX_HOME/skills or ~/.codex/skills')
args = parser.parse_args()
parent = Path(args.dest).expanduser() if args.dest else Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex'))) / 'skills'
target = parent / 'series-english'
if target.exists():
    parser.error('目标已存在；请先自行备份旧版或选择其他 --dest。安装器不会覆盖。')
source = Path(__file__).resolve().parents[1] / 'skills' / 'series-english'
shutil.copytree(source, target)
print('Installed:', target.resolve())
print('在支持 Skills 的宿主中重新加载技能列表，再使用 $series-english。')
