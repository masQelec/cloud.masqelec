#!/usr/bin/env python3
"""Prepare and publish Tvheadend releases in cloud.masqelec (Python 3.8+)."""
import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ADDON = 'service.tvheadend43'
BASE = Path('pvr/tvheadend')
MANIFEST = BASE / 'manifest.json'
COMPAT = Path('tools/update_tvheadend/compatibility.json')
TARGETS = {'Amlogic-ng.arm': (1, 40), 'Amlogic-ne.aarch64': (2, 183)}
PART = r'(?:0|[1-9][0-9]{0,3})'
VERSION = re.compile(PART + r'\.' + PART + r'\.' + PART)
CORE_VERSION = re.compile(PART + r'\.' + PART + r'(?:\.' + PART + r')?')
BUILD = re.compile(r'[A-Za-z0-9_.+-]{1,128}')
SHA = re.compile(r'[0-9a-f]{64}')
NAME = re.compile(re.escape(ADDON) + r'-(.+)\.zip')
REMOTE = {'git@github.com:masQelec/cloud.masqelec.git',
          'git@github.com:masQelec/cloud.masqelec',
          'ssh://git@github.com/masQelec/cloud.masqelec.git',
          'https://github.com/masQelec/cloud.masqelec.git',
          'https://github.com/masQelec/cloud.masqelec'}


class ReleaseError(Exception):
    pass


def require(value, message):
    if not value:
        raise ReleaseError(message)


def match(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def ver(value):
    require(match(VERSION, value), 'Invalid version: ' + str(value))
    return tuple(map(int, value.split('.')))


def package_path(target, version):
    return BASE / target / (ADDON + '-' + version + '.zip')


def safe_path(path):
    for part in (path, *path.parents):
        require(not part.is_symlink(), 'Symlink rejected: ' + str(part))


def regular(path):
    safe_path(path)
    require(path.is_file(), 'Missing/nonregular file: ' + str(path))


def json_bytes(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def unique(pairs):
    data = {}
    for key, value in pairs:
        require(key not in data, 'Duplicate JSON key: ' + key)
        data[key] = value
    return data


def read_json(path, limit=65536):
    regular(path)
    require(0 < path.stat().st_size <= limit, 'Invalid JSON size: ' + str(path))
    return json.loads(path.read_bytes().decode('utf-8'), object_pairs_hook=unique)


def atomic_write(path, content):
    safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as out:
            os.fchmod(out.fileno(), 0o644)
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def builds(value):
    require(isinstance(value, list) and len(value) <= 128, 'Invalid build list')
    seen = set()
    for row in value:
        require(isinstance(row, dict) and set(row) == {'version_id', 'build'}, 'Invalid build entry')
        require(match(CORE_VERSION, row['version_id']) and match(BUILD, row['build']), 'Invalid build identity')
        key = (row['version_id'], row['build'])
        require(key not in seen, 'Duplicate build')
        seen.add(key)
    return sorted(value, key=lambda x: (x['version_id'], x['build']))


def check_manifest(data, major):
    require(isinstance(data, dict) and set(data) == {'schema', 'addon_id', 'kodi_major', 'packages'}, 'Invalid manifest fields')
    require(type(data['schema']) is int and data['schema'] == 1 and data['addon_id'] == ADDON and type(data['kodi_major']) is int and data['kodi_major'] == major, 'Manifest identity mismatch')
    entries = data['packages']
    require(isinstance(entries, list) and 0 < len(entries) <= len(TARGETS), 'Invalid package list')
    found = {}
    for item in entries:
        require(isinstance(item, dict) and set(item) == {'target','version','path','size','sha256','validated_builds'}, 'Invalid package fields')
        target = item['target']
        require(isinstance(target, str) and target in TARGETS and target not in found, 'Invalid/duplicate target')
        ver(item['version'])
        require(item['path'] == package_path(target, item['version']).as_posix(), 'Invalid package path')
        require(type(item['size']) is int and 0 < item['size'] <= 100*1024*1024 and match(SHA, item['sha256']), 'Invalid package size/hash')
        builds(item['validated_builds'])
        found[target] = item
    return found


def check_compat(data):
    require(isinstance(data, dict) and set(data) == {'schema','approvals'} and type(data['schema']) is int and data['schema'] == 1 and isinstance(data['approvals'], list), 'Invalid compatibility file')
    result = {}
    for item in data['approvals']:
        require(isinstance(item, dict) and set(item) == {'target','version','sha256','validated_builds'}, 'Invalid approval')
        require(isinstance(item['target'], str) and item['target'] in TARGETS and match(SHA,item['sha256']), 'Invalid approval identity')
        ver(item['version'])
        key = (item['target'], item['version'], item['sha256'])
        require(key not in result, 'Duplicate approval')
        result[key] = builds(item['validated_builds'])
    return result


def validate_zip(path, target, version):
    regular(path)
    size = path.stat().st_size
    require(0 < size <= 100*1024*1024, 'ZIP size limit: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(262144), b''):
            digest.update(chunk)
        require(stream.tell() == size, 'ZIP changed during hash')
        stream.seek(0)
        with zipfile.ZipFile(stream) as z:
            infos = z.infolist()
            require(0 < len(infos) <= 8192, 'Invalid ZIP member count')
            names = {}
            unpacked = 0
            for info in infos:
                name = info.filename
                canonical = name.rstrip('/')
                parts = canonical.split('/')
                require(info.orig_filename == name and '\\' not in name and ':' not in name and not any(ord(c)<32 or ord(c)==127 for c in name) and all(p not in ('','.','..') for p in parts) and parts[0] == ADDON, 'Unsafe ZIP path')
                is_dir = info.is_dir()
                mode = info.external_attr >> 16
                require(canonical not in names and stat.S_IFMT(mode) in (0, stat.S_IFDIR if is_dir else stat.S_IFREG) and not mode & 0o7000, 'Unsafe/duplicate ZIP member')
                require(not info.flag_bits & 1 and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'Unsupported ZIP member')
                require(len(parts)>1 or is_dir, 'Invalid ZIP root')
                require(not is_dir or info.file_size == 0, 'Invalid ZIP directory')
                names[canonical] = is_dir
                unpacked += info.file_size
                require(unpacked <= 512*1024*1024, 'ZIP unpacked size limit')
            for name in names:
                parts = name.split('/')
                for i in range(1,len(parts)):
                    require(names.get('/'.join(parts[:i])) is not False, 'ZIP parent file conflict')
            xml = ADDON + '/addon.xml'
            binary = ADDON + '/bin/tvheadend'
            require(names.get(xml) is False and names.get(binary) is False, 'Missing addon.xml or tvheadend')
            require(0 < z.getinfo(xml).file_size <= 256*1024, 'Invalid addon.xml size')
            text = z.read(xml).decode('utf-8-sig')
            require('<!DOCTYPE' not in text and '<!ENTITY' not in text, 'Unsafe addon.xml')
            root = ET.fromstring(text)
            require(root.tag == 'addon' and root.get('id') == ADDON and root.get('version') == version, 'ZIP addon ID/version mismatch')
            with z.open(binary) as exe:
                h = exe.read(64)
            cls, machine = TARGETS[target]
            require(len(h)>=20 and h[:4]==b'\x7fELF' and h[4]==cls and h[5:7]==b'\x01\x01' and int.from_bytes(h[16:18],'little') in (2,3) and int.from_bytes(h[18:20],'little')==machine, 'ELF architecture mismatch')
            require(z.testzip() is None, 'ZIP CRC error')
    return {'target':target,'version':version,'path':path.as_posix(),'size':size,'sha256':digest.hexdigest(),'validated_builds':[]}


def scan():
    found = {}
    safe_path(BASE)
    for target in TARGETS:
        folder = BASE / target
        safe_path(folder)
        if not folder.exists():
            continue
        require(folder.is_dir(), 'Invalid target folder')
        candidates = []
        for path in folder.iterdir():
            if not path.name.lower().endswith('.zip'):
                continue
            m = NAME.fullmatch(path.name)
            require(m is not None, 'Invalid ZIP name: '+str(path))
            release = m.group(1)
            ver(release)
            regular(path)
            candidates.append((ver(release), release, path))
        if candidates:
            _, release, path = max(candidates)
            found[target] = validate_zip(path,target,release)
    return found


def git(*args):
    return subprocess.check_output(['git',*args], stderr=None).decode('utf-8').strip()


def git_run(*args):
    subprocess.run(['git',*args],check=True)


def check_remote():
    for args in (('remote','get-url','--all','origin'),('remote','get-url','--push','--all','origin')):
        urls = git(*args).splitlines()
        require(len(urls)==1 and urls[0] in REMOTE, 'Unexpected origin URL')


def status():
    raw = subprocess.check_output(['git','status','--porcelain=v1','-z','--untracked-files=all','--no-renames'])
    result = {}
    for row in raw.split(b'\0'):
        if row:
            require(len(row)>=4 and row[2:3]==b' ', 'Unexpected Git status')
            result[os.fsdecode(row[3:])] = row[:2].decode('ascii')
    return result


def check_worktree(changes):
    for name, state in changes.items():
        p = Path(name)
        require(state in ('??',' D') and len(p.parts)==4 and p.parts[:2]==BASE.parts and p.parts[2] in TARGETS and NAME.fullmatch(p.name), 'Unrelated/staged/modified/deleted file: '+name)
        if state == '??':
            regular(p)
        else:
            safe_path(p)
        ver(NAME.fullmatch(p.name).group(1))


def remote_head(branch):
    lines = git('ls-remote','--exit-code','origin','refs/heads/'+branch).splitlines()
    require(len(lines)==1 and lines[0].split()[1]=='refs/heads/'+branch, 'Remote branch not confirmed')
    return lines[0].split()[0]


def plan(major, approvals_args):
    previous = check_manifest(read_json(MANIFEST),major) if MANIFEST.exists() else {}
    approvals = check_compat(read_json(COMPAT))
    selected = scan()
    require(bool(selected) or not previous, 'No packages remain')
    for target, old in previous.items():
        require(target in selected, 'Previously published target missing: '+target)
        current = selected[target]
        require(ver(current['version'])>=ver(old['version']), 'Downgrade blocked: '+target)
        old_path = Path(old['path'])
        safe_path(old_path)
        # The old ZIP may have been deliberately removed when replacing it.
        if old_path.exists():
            prior = current if current['version']==old['version'] else validate_zip(old_path,target,old['version'])
            require(prior['sha256']==old['sha256'] and prior['size']==old['size'], 'Previously published ZIP changed: '+target)
        else:
            require(ver(current['version'])>ver(old['version']), 'Previously published ZIP missing: '+target)
            print('OLD_ZIP_MISSING_REPLACED='+str(old_path))
    for target, release, core, build in approvals_args:
        require(target in selected and selected[target]['version']==release, 'Approval must match selected target/version')
        require(match(CORE_VERSION,core) and match(BUILD,build), 'Invalid approval build')
        row=selected[target]
        key=(target,release,row['sha256'])
        old_builds=approvals.setdefault(key,[])
        item={'version_id':core,'build':build}
        if item not in old_builds:
            old_builds.append(item)
    for target, row in selected.items():
        key=(target,row['version'],row['sha256'])
        old=previous.get(target)
        approved=list(approvals.get(key,[]))
        if old and old['version']==row['version'] and old['sha256']==row['sha256']:
            for item in old['validated_builds']:
                if item not in approved:
                    approved.append(item)
        row['validated_builds']=builds(approved)
        require(bool(approved), 'No physical build approval: '+target+' '+row['version']+' SHA256='+row['sha256'])
        if key in approvals:
            approvals[key]=builds(approved)
    if not selected:
        require(not approvals_args,'No packages to approve')
        return None, None, []
    manifest={'schema':1,'addon_id':ADDON,'kodi_major':major,'packages':[selected[k] for k in sorted(selected)]}
    check_manifest(manifest,major)
    compat={'schema':1,'approvals':[{'target':k[0],'version':k[1],'sha256':k[2],'validated_builds':builds(v)} for k,v in sorted(approvals.items())]}
    require(len(json_bytes(manifest))<=65536 and len(json_bytes(compat))<=65536,'JSON size limit')
    return manifest,compat,[Path(row['path']) for row in selected.values()]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true',help='Validate without writing, committing, fetching or pushing')
    parser.add_argument('--approve',nargs=4,action='append',default=[],metavar=('TARGET','TVH_VERSION','CORE_VERSION','CORE_BUILD'),help='Attest this exact ZIP/build was physically validated; repeat as needed')
    args=parser.parse_args(argv)
    root=Path(git('rev-parse','--show-toplevel'))
    os.chdir(root)
    branch=git('branch','--show-current')
    require(re.fullmatch(r'[1-9][0-9]?',branch) is not None,'Only a numeric Kodi branch is allowed')
    check_remote()
    check_worktree(status())
    head=git('rev-parse','HEAD')
    if not args.dry_run:
        require(remote_head(branch)==head,'Local/remote differ; sync or review previous failed push first')
    manifest,compat,packages=plan(int(branch),args.approve)
    if manifest is None:
        require(not status(), 'No packages remain but Git has changes')
        print('NO_PACKAGES: no changes, no push')
        return 0
    # Preserve semantic equality (formatting alone does not create a release).
    changed={}
    for path,data in ((MANIFEST,manifest),(COMPAT,compat)):
        if not path.exists() or read_json(path)!=data:
            changed[path]=json_bytes(data)
    untracked=status()
    new_packages=[p for p in packages if untracked.get(p.as_posix())=='??']
    for p in packages:
        if p not in new_packages:
            # Reject ignored or otherwise untracked ZIPs before modifying JSON.
            require(git('ls-files','--',p.as_posix())==p.as_posix(),'Selected ZIP not tracked or visible to Git: '+str(p))
    deleted=[]
    selected={row['target']:row for row in manifest['packages']}
    previous=check_manifest(read_json(MANIFEST),int(branch)) if MANIFEST.exists() else {}
    for name,state in untracked.items():
        if state!=' D':
            continue
        p=Path(name); target=p.parts[2]; release=NAME.fullmatch(p.name).group(1)
        require(target in selected and target in previous and ver(selected[target]['version'])>ver(previous[target]['version']) and ver(release)<ver(selected[target]['version']), 'ZIP deletion requires newer authorized release: '+name)
        deleted.append(p)
    paths=sorted(set(changed)|set(new_packages)|set(deleted))
    print(json_bytes(manifest).decode(),end='')
    print('RELEASE_FILES='+','.join(str(p) for p in paths))
    if not paths:
        print('UP_TO_DATE: no commit, no push')
        return 0
    if args.dry_run:
        print('DRY_RUN=PASS; no writes, commit or push')
        return 0
    # Ensure status and remote have not changed since plan. No force-push.
    current_status=status()
    check_worktree(current_status)
    require(current_status==untracked,'Working tree changed during validation')
    require(git('rev-parse','HEAD')==head and remote_head(branch)==head,'Concurrent branch change')
    for path,content in changed.items():
        atomic_write(path,content)
    # Revalidate candidate bytes and ensure the actual staged blobs match.
    for row in manifest['packages']:
        fresh=validate_zip(Path(row['path']),row['target'],row['version'])
        require(fresh['sha256']==row['sha256'] and fresh['size']==row['size'],'ZIP changed before staging')
    git_run('add','--',*(str(p) for p in paths))
    actual=set(git('diff','--cached','--name-only').splitlines())
    require(actual=={p.as_posix() for p in paths},'Unexpected staged files')
    for row in manifest['packages']:
        blob=subprocess.check_output(['git','show',':'+row['path']])
        require(len(blob)==row['size'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Staged ZIP hash mismatch')
    for path,data in ((MANIFEST,manifest),(COMPAT,compat)):
        blob=subprocess.check_output(['git','show',':'+path.as_posix()])
        require(json.loads(blob.decode('utf-8'),object_pairs_hook=unique)==data,'Staged JSON mismatch')
    git_run('diff','--cached','--check')
    summary=', '.join(row['target']+' '+row['version'] for row in manifest['packages'])
    git_run('commit','-m','Release Tvheadend for Kodi '+branch+': '+summary)
    commit=git('rev-parse','HEAD')
    require(git('rev-parse','HEAD^')==head,'Unexpected commit parent')
    require(set(git('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines())==actual,'Unexpected committed files; push blocked')
    # Check committed blobs again, including potential hook changes.
    for row in manifest['packages']:
        blob=subprocess.check_output(['git','show',commit+':'+row['path']])
        require(len(blob)==row['size'] and hashlib.sha256(blob).hexdigest()==row['sha256'],'Committed ZIP mismatch')
    for path,data in ((MANIFEST,manifest),(COMPAT,compat)):
        blob=subprocess.check_output(['git','show',commit+':'+path.as_posix()])
        require(json.loads(blob.decode('utf-8'),object_pairs_hook=unique)==data,'Committed JSON mismatch')
    require(remote_head(branch)==head,'Remote advanced; local commit preserved, push blocked')
    git_run('push','--no-follow-tags','--recurse-submodules=no','origin',commit+':refs/heads/'+branch)
    require(remote_head(branch)==commit,'Push returned but remote tip not confirmed; inspect remote')
    print('COMMIT='+commit)
    print('REMOTE_COMMIT='+commit)
    print('RELEASE_PUBLISHED=PASS')
    return 0


if __name__=='__main__':
    try:
        sys.exit(main())
    except (ReleaseError, OSError, ValueError, TypeError, KeyError, ET.ParseError, zipfile.BadZipFile, subprocess.CalledProcessError, RuntimeError) as error:
        print('RELEASE_BLOCKED: '+str(error),file=sys.stderr)
        print('Inspect git status and remote before retrying; no automatic reset or force-push.',file=sys.stderr)
        sys.exit(1)
