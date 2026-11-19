"""Read-only, bounded metadata inventory; never reads project file content."""
import argparse
import os
import subprocess
import selectors
import signal
import time
from pathlib import Path
from common import emit

EXCLUDE = {'.git', '.env', '.aws', '.ssh', '.codex', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', 'logs', 'runs', 'cache', '.cache'}

def inspect(root, allowed, max_entries=300, max_size=1048576, include_git=False):
    root = Path(root).absolute()
    if root.is_symlink() or root.resolve() != root or not root.is_dir():
        raise ValueError('root must be an existing canonical directory without symlinks')
    if not allowed or not 1 <= max_entries <= 2000 or not 1 <= max_size <= 10485760:
        raise ValueError('explicit allow list and bounded limits required')
    paths = []
    for rel in allowed:
        p = Path(rel)
        if p.is_absolute() or '..' in p.parts:
            raise ValueError('allow paths must stay within root')
        paths.append(root / p)
    out = {'scope': str(root), 'entries': [], 'skipped': {}, 'errors': [], 'remote': 'not_run', 'content_reads': 0}
    deadline = time.monotonic() + 3
    seen = set()
    def skip(reason):
        out['skipped'][reason] = out['skipped'].get(reason, 0) + 1
    stack = paths[:]
    while stack:
        if len(seen) >= max_entries or time.monotonic() > deadline:
            skip('inventory_limit'); break
        p = stack.pop()
        rel = p.relative_to(root)
        if p in seen: continue
        seen.add(p)
        if any(x in EXCLUDE or x.startswith('.env') or any(s in x.lower() for s in ('credential', 'secret', 'token', 'password')) for x in rel.parts):
            skip('excluded'); continue
        try:
            if p.is_symlink() or p.resolve() != p:
                skip('symlink'); continue
            stat = p.stat()
            if p.is_dir():
                with os.scandir(p) as entries:
                    for entry in entries:
                        if len(stack) + len(seen) >= max_entries:
                            skip('inventory_limit'); break
                        stack.append(Path(entry.path))
            elif p.is_file():
                if stat.st_size > max_size: skip('large_file'); continue
                out['entries'].append({'path': str(rel), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns})
            else: skip('non_regular')
        except OSError:
            out['errors'].append('metadata_unavailable')
    keys = ('root', 'git_dir', 'common_dir', 'branch', 'head')
    out['git'] = {key: {'state':'unknown', 'reason':'git_not_requested'} for key in keys}
    out['git']['tracked_changes'] = {'state':'unknown', 'count':None,
        'reason':'worktree_content_queries_disabled', 'untracked':'not_assessed'}
    out['coverage'] = 'metadata_only_bounded; no file content, product execution, or online facts'
    if not include_git:
        return out
    git_entry = root / '.git'
    if git_entry.is_symlink() or git_entry.is_file() or (git_entry / 'commondir').exists():
        for key in keys:
            out['git'][key] = {'state':'unknown', 'reason':'external_or_linked_git_metadata_not_supported'}
        return out
    # Opt-in permits metadata of this root, never automatic parent discovery.
    # Avoid inherited Git overrides pointing to a different repository.
    env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_CEILING_DIRECTORIES=str(root.parent))
    def git(args):
        try:
            proc = subprocess.Popen(['git', '--literal-pathspecs', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-C', str(root), *args], env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
            output=bytearray(); end=time.monotonic()+2
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                try:
                    while True:
                        remaining=end-time.monotonic()
                        if remaining<=0 or not selector.select(remaining):
                            return {'state':'unknown','reason':'timeout'}
                        chunk=os.read(proc.stdout.fileno(),4096)
                        if not chunk: break
                        output.extend(chunk)
                        if len(output)>8192: return {'state':'unknown','reason':'output_limit'}
                    code=proc.wait(timeout=max(0.01,end-time.monotonic()))
                    return {'state':'observed' if code==0 else 'unknown','value':output.decode('utf-8','replace').strip() if code==0 else None}
                finally:
                    # Parent may already have exited while descendants still own stdout.
                    try: os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    proc.wait(); proc.stdout.close()
        except (OSError, subprocess.TimeoutExpired):
            return {'state':'unknown', 'reason':'git_unavailable_or_timeout'}
    out['git'] = {key:git(args) for key,args in {
        'root':['rev-parse','--show-toplevel'], 'git_dir':['rev-parse','--absolute-git-dir'],
        'common_dir':['rev-parse','--git-common-dir'], 'branch':['symbolic-ref','--short','HEAD'],
        'head':['rev-parse','--verify','HEAD']}.items()}
    # Worktree diff/status can invoke clean/process filters and read excluded files.
    # Do not query changes at all: absence of a query must never become zero changes.
    out['git']['tracked_changes'] = {'state':'unknown', 'count':None,
        'reason':'worktree_content_queries_disabled', 'untracked':'not_assessed'}
    out['coverage'] = 'metadata_only_bounded; no file content, product execution, or online facts'
    return out

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('root'); p.add_argument('--allow',action='append',required=True); p.add_argument('--max-entries',type=int,default=300); p.add_argument('--max-size',type=int,default=1048576); p.add_argument('--include-git',action='store_true',help='Explicitly permitted repository metadata; no parent discovery')
    a=p.parse_args()
    try: emit(inspect(a.root,a.allow,a.max_entries,a.max_size,a.include_git))
    except (ValueError,OSError): emit({'state':'unknown','reason':'invalid_or_unavailable_scope'}); raise SystemExit(2)
