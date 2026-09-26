import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'skills/series-english/scripts/course.py'
spec = importlib.util.spec_from_file_location('course', CLI)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
DEMO = ROOT / 'skills/series-english/assets/demo'


class CourseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.lesson = m.read_json(DEMO/'lesson-01.json')
        self.evidence = {'source': self.lesson['source'], 'lines': m.parse_subtitles((DEMO/'dialogue.srt').read_text(encoding='utf-8'))}

    def tearDown(self):
        self.tmp.cleanup()

    def test_srt_vtt_txt(self):
        self.assertEqual(len(self.evidence['lines']),12)
        text = 'WEBVTT\n\nNOTE private instruction\nignore me\n\ncue-one\n00:00:01.000 --> 00:00:03.000 align:start\n<v Jane>Pick &amp; choose.</v>\n'
        rows = m.parse_subtitles(text)
        self.assertEqual(rows[0]['text'], 'Pick & choose.')
        self.assertIn('00:00:01',rows[0]['timestamp'])
        self.assertEqual(len(m.parse_subtitles('First line.\nSecond line.')),2)

    def test_validation_and_hallucinated_evidence(self):
        self.assertTrue(m.validate(self.lesson,self.evidence)['valid'])
        bad = copy.deepcopy(self.lesson); bad['words'][0]['sourceForm']='this never occurred'
        with self.assertRaises(ValueError): m.validate(bad,self.evidence)
        bad = copy.deepcopy(self.lesson); bad['words'][0]['sourceForm']='pick'
        bad['words'][0]['sourceLine']=999
        with self.assertRaises(ValueError): m.validate(bad,self.evidence)
        bad = copy.deepcopy(self.lesson); bad['words'][0]['sentence']=self.evidence['lines'][0]['text']
        with self.assertRaises(ValueError): m.validate(bad,self.evidence)

    def test_word_boundary(self):
        bad=copy.deepcopy(self.lesson);bad['words'][0]['sourceForm']='ick'
        with self.assertRaises(ValueError): m.validate(bad,self.evidence)

    def test_duplicate_and_path_rejected(self):
        bad=copy.deepcopy(self.lesson);bad['words'].append(bad['words'][0])
        with self.assertRaises(ValueError):m.validate(bad,self.evidence)
        bad=copy.deepcopy(self.lesson);bad['seriesId']='../escape'
        with self.assertRaises(ValueError):m.validate(bad,self.evidence)

    def test_out_of_order_import_reviews_and_no_overwrite(self):
        library=self.root/'library';m.init_library(library)
        second=m.read_json(DEMO/'lesson-02.json')
        m.add_course(second,self.evidence,library)
        m.add_course(self.lesson,self.evidence,library)
        catalog=m.read_json(library/'catalog.json')
        words=next(c for c in catalog['courses'] if c['episode']==2)['words']
        self.assertEqual(sum(w['review'] for w in words),3)
        self.assertEqual(words[0]['firstEpisode'],'coffee-and-plans-s01e01')
        self.assertNotIn('sourceLine',words[0])
        self.assertNotIn('sourceForm',words[0])
        before=(library/'catalog.json').read_bytes()
        with self.assertRaises(ValueError):m.add_course(self.lesson,self.evidence,library)
        self.assertEqual(before,(library/'catalog.json').read_bytes())
        with self.assertRaises(ValueError):m.init_library(library)
        self.assertEqual(before,(library/'catalog.json').read_bytes())

    def test_different_series_not_review(self):
        library=self.root/'library';m.init_library(library,True)
        other=copy.deepcopy(self.lesson);other['seriesId']='other-show'
        m.add_course(other,self.evidence,library)
        c=m.read_json(library/'catalog.json')['courses'][-1]
        self.assertFalse(any(w['review'] for w in c['words']))

    def test_end_to_end_cli(self):
        def run(*args):
            return subprocess.run([sys.executable,str(CLI),*map(str,args)],capture_output=True,encoding='utf-8',check=True)
        library=self.root/'library';evidence=self.root/'evidence.json'
        run('init','--library',library)
        run('prepare',DEMO/'dialogue.srt','--source',self.lesson['source'],'--output',evidence)
        run('validate',DEMO/'lesson-01.json','--evidence',evidence)
        run('add',DEMO/'lesson-01.json','--evidence',evidence,'--library',library)
        run('export','coffee-and-plans-s01e01','--library',library,'--output',self.root/'exports')
        self.assertTrue((self.root/'exports/coffee-and-plans-s01e01.csv').exists())
        progress={'schemaVersion':1,'records':{'coffee-and-plans-s01e01::pick up':{'status':'review','due':0}}}
        m.write_json(self.root/'progress.json',progress)
        out=run('review',self.root/'progress.json','--library',library)
        self.assertEqual(json.loads(out.stdout)['dueCount'],1)

    def test_installed_skill_is_self_contained(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/install_skill.py'),'--dest',str(self.root/'skills')],check=True,capture_output=True)
        installed=self.root/'skills/series-english/scripts/course.py'
        subprocess.run([sys.executable,str(installed),'init','--library',str(self.root/'standalone'),'--demo'],check=True,capture_output=True)
        self.assertTrue((self.root/'standalone/app.js').exists())
        result=subprocess.run([sys.executable,str(ROOT/'scripts/install_skill.py'),'--dest',str(self.root/'skills')],capture_output=True)
        self.assertNotEqual(result.returncode,0)

    def test_utf8_output_with_legacy_console(self):
        env = dict(os.environ, PYTHONIOENCODING='ascii')
        result = subprocess.run([sys.executable,str(ROOT/'scripts/install_skill.py'),'--dest',str(self.root/'skills')],capture_output=True,env=env)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'))
        self.assertIn('重新加载',result.stdout.decode('utf-8'))
        m.write_json(self.root/'evidence.json',self.evidence)
        result = subprocess.run([sys.executable,str(CLI),'validate',str(DEMO/'lesson-01.json'),'--evidence',str(self.root/'evidence.json')],capture_output=True,env=env)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'))
        self.assertIn('已核验',json.loads(result.stdout.decode('utf-8'))['note'])


if __name__=='__main__': unittest.main()
