import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import update_tvheadend as tool

NG='Amlogic-ng.arm'
NE='Amlogic-ne.aarch64'
CORE='21.2.5'
BUILD='21.2.5-Omega_devel_20250919152246'


def make_zip(target, version, *, elf_target=None, xml_version=None, extra=None):
    path=tool.package_path(target,version)
    path.parent.mkdir(parents=True,exist_ok=True)
    cls,machine=tool.TARGETS[elf_target or target]
    header=bytearray(64)
    header[:7]=b'\x7fELF'+bytes([cls,1,1])
    header[16:18]=(3).to_bytes(2,'little')
    header[18:20]=machine.to_bytes(2,'little')
    with zipfile.ZipFile(path,'w') as z:
        z.writestr(tool.ADDON+'/addon.xml',f'<addon id="{tool.ADDON}" version="{xml_version or version}"/>')
        z.writestr(tool.ADDON+'/bin/tvheadend',header)
        if extra:
            z.writestr(extra,'test')
    return path


class GitLab(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.old=Path.cwd()
        self.addCleanup(os.chdir,self.old)
        base=Path(self.temp.name)
        self.remote=base/'remote.git'
        self.repo=base/'repo'
        subprocess.run(['git','init','--bare','-q',str(self.remote)],check=True)
        subprocess.run(['git','init','-q','-b','21',str(self.repo)],check=True)
        os.chdir(self.repo)
        tool.git_run('config','user.name','Lab')
        tool.git_run('config','user.email','lab@example.invalid')
        tool.git_run('remote','add','origin',str(self.remote))
        tool.COMPAT.parent.mkdir(parents=True)
        tool.COMPAT.write_bytes(tool.json_bytes({'schema':1,'approvals':[]}))
        tool.git_run('add','--',str(tool.COMPAT))
        tool.git_run('commit','-qm','Initial')
        tool.git_run('push','-q','origin','21')
        self.initial=tool.git('rev-parse','HEAD')
        # Only the production URL allowlist is replaced. Real commits and pushes
        # are performed against an isolated bare Git repository.
        p=patch.object(tool,'REMOTE',{str(self.remote)})
        p.start(); self.addCleanup(p.stop)

    def run_tool(self,*args):
        with contextlib.redirect_stdout(io.StringIO()):
            return tool.main(list(args))

    def approve(self,target=NG,version='21.2.9'):
        return ['--approve',target,version,CORE,BUILD]

    def current(self):
        return tool.check_manifest(tool.read_json(tool.MANIFEST),21)

    def test_first_publish_and_idempotence(self):
        p=make_zip(NG,'21.2.9')
        self.assertEqual(self.run_tool(*self.approve()),0)
        head=tool.git('rev-parse','HEAD')
        self.assertNotEqual(head,self.initial)
        self.assertEqual(head,tool.remote_head('21'))
        self.assertEqual(self.current()[NG]['version'],'21.2.9')
        self.assertEqual(subprocess.check_output(['git','show','HEAD:'+str(p)]),p.read_bytes())
        self.assertEqual(self.run_tool(),0)
        self.assertEqual(tool.git('rev-parse','HEAD'),head)

    def test_dry_run(self):
        make_zip(NG,'21.2.9')
        self.run_tool('--dry-run',*self.approve())
        self.assertFalse(tool.MANIFEST.exists())
        self.assertEqual(tool.git('rev-parse','HEAD'),self.initial)
        self.assertEqual(tool.remote_head('21'),self.initial)

    def test_approval_required(self):
        make_zip(NG,'21.2.9')
        with self.assertRaisesRegex(tool.ReleaseError,'No physical build approval'):
            self.run_tool()
        self.assertFalse(tool.MANIFEST.exists())
        self.assertEqual(tool.remote_head('21'),self.initial)

    def test_latest_numeric_and_two_architectures(self):
        make_zip(NG,'21.2.9')
        make_zip(NG,'21.2.10')
        make_zip(NE,'21.2.8')
        self.run_tool(*self.approve(NG,'21.2.10'),*self.approve(NE,'21.2.8'))
        self.assertEqual(self.current()[NG]['version'],'21.2.10')
        self.assertEqual(self.current()[NE]['version'],'21.2.8')
        self.assertIn(str(tool.package_path(NG,'21.2.9')),tool.status())

    def test_new_version_does_not_inherit_approval(self):
        make_zip(NG,'21.2.9')
        self.run_tool(*self.approve())
        make_zip(NG,'21.2.10')
        with self.assertRaisesRegex(tool.ReleaseError,'No physical build approval'):
            self.run_tool()
        self.run_tool(*self.approve(NG,'21.2.10'))
        self.assertEqual(self.current()[NG]['version'],'21.2.10')
        self.assertTrue(tool.package_path(NG,'21.2.9').exists())

    def test_wrong_architecture(self):
        make_zip(NG,'21.2.9',elf_target=NE)
        with self.assertRaisesRegex(tool.ReleaseError,'ELF architecture'):
            self.run_tool(*self.approve())
        self.assertEqual(tool.remote_head('21'),self.initial)

    def test_wrong_xml_version(self):
        make_zip(NG,'21.2.9',xml_version='21.2.8')
        with self.assertRaisesRegex(tool.ReleaseError,'ID/version'):
            self.run_tool(*self.approve())

    def test_unsafe_zip(self):
        make_zip(NG,'21.2.9',extra=tool.ADDON+'/../escape')
        with self.assertRaisesRegex(tool.ReleaseError,'Unsafe ZIP path'):
            self.run_tool(*self.approve())

    def test_corrupt_zip(self):
        p=make_zip(NG,'21.2.9'); p.write_bytes(b'bad')
        with self.assertRaises(zipfile.BadZipFile):
            self.run_tool(*self.approve())

    def test_unrelated_changes_blocked(self):
        make_zip(NG,'21.2.9'); Path('unrelated').write_text('private')
        with self.assertRaisesRegex(tool.ReleaseError,'Unrelated'):
            self.run_tool(*self.approve())

    def test_modified_published_zip_blocked(self):
        p=make_zip(NG,'21.2.9'); self.run_tool(*self.approve())
        with p.open('ab') as out: out.write(b'changed')
        with self.assertRaisesRegex(tool.ReleaseError,'Unrelated'):
            self.run_tool()

    def test_deleted_published_zip_blocked(self):
        p=make_zip(NG,'21.2.9'); self.run_tool(*self.approve())
        p.unlink(); make_zip(NG,'21.2.8')
        with self.assertRaisesRegex(tool.ReleaseError,'Downgrade'):
            self.run_tool()

    def test_replace_only_zip(self):
        p=make_zip(NG,'21.2.9'); self.run_tool(*self.approve())
        p.unlink(); new=make_zip(NG,'21.2.10')
        self.run_tool(*self.approve(NG,'21.2.10'))
        self.assertFalse(p.exists())
        self.assertEqual(self.current()[NG]['version'],'21.2.10')
        self.assertEqual(tool.remote_head('21'),tool.git('rev-parse','HEAD'))
        self.assertEqual(subprocess.check_output(['git','show','HEAD:'+str(new)]),new.read_bytes())
        self.assertEqual(tool.status(),{})

    def test_local_ahead_blocked(self):
        tool.git_run('commit','--allow-empty','-qm','Other local commit')
        make_zip(NG,'21.2.9')
        with self.assertRaisesRegex(tool.ReleaseError,'Local/remote differ'):
            self.run_tool(*self.approve())
        self.assertEqual(tool.remote_head('21'),self.initial)

    def test_same_version_other_hash_even_if_committed(self):
        p=make_zip(NG,'21.2.9'); self.run_tool(*self.approve())
        with p.open('ab') as out: out.write(b'changed')
        tool.git_run('add','--',str(p)); tool.git_run('commit','-qm','external modification')
        tool.git_run('push','-q','origin','21')
        with self.assertRaisesRegex(tool.ReleaseError,'Previously published ZIP changed'):
            self.run_tool()

    def test_non_numeric_branch_blocked(self):
        tool.git_run('switch','-qc','develop')
        with self.assertRaisesRegex(tool.ReleaseError,'numeric Kodi'):
            self.run_tool()

    def test_no_packages(self):
        self.run_tool()
        self.assertFalse(tool.MANIFEST.exists())
        self.assertEqual(tool.remote_head('21'),self.initial)


if __name__=='__main__': unittest.main()
