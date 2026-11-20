# Επεξήγηση: Ελέγχει κυρίως απαγορευμένες προσβάσεις, ανακλήσεις και διατήρηση δεδομένων.
"""Data preservation and negative-path authorisation, entirely offline in disposable DBs."""
import dataclasses
import json
import sqlite3
import time
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import db, profile, sharing, twin, retrieval, jobs, voice
from app.context import CURRENT_PERSON, CURRENT_VIEWER, as_person
from app.main import app, bootstrap
from app.config import settings


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, '_CONN', None)
    monkeypatch.setattr(db, 'settings', dataclasses.replace(settings, data_dir=tmp_path))
    monkeypatch.setattr(retrieval, '_INDEXES', {})
    monkeypatch.setattr(jobs, '_JOBS', {})
    viewer = CURRENT_VIEWER.set(None)
    person = CURRENT_PERSON.set('ceo')
    yield
    if db._CONN is not None:
        db._CONN.close()
    CURRENT_PERSON.reset(person)
    CURRENT_VIEWER.reset(viewer)


def login(c, user='ceo', password='ceo2026'):
    r = c.post('/api/login', json={'username': user, 'password': password})
    assert r.status_code == 200
    c.cookies.clear()
    return {'Authorization': 'Bearer ' + r.json()['token']}


def add(c, headers, text='ΔΟΚΙΜΑΣΤΙΚΟΣ εταιρικός κανόνας: pilot χωρίς αποκλειστικότητα.', section='decision_rules', scope='company'):
    r = c.post('/api/profile/traits', headers=headers, json={'section': section, 'text': text, 'scope': scope})
    assert r.status_code == 200, r.text
    return r.json()[section][-1]['id']


def review(c, headers, tid):
    return next(t for t in c.get('/api/self-test', headers=headers).json()['company_rules'] if t['id']==tid)


def publish(c, headers, tid):
    rule = review(c, headers, tid)
    r = c.post(f'/api/profile/traits/{tid}/publication', headers=headers,
               json={'published': True, 'content_hash': rule['content_hash']})
    assert r.status_code == 200, r.text


def inherited(c, h):
    p = c.get('/api/profile', headers=h).json()
    return p['inherited']['decision_rules'] + p['inherited']['values']


@pytest.mark.parametrize('edit_profile', [False, True])
def test_startup_preserves_data_sessions_identity_and_profiles(monkeypatch, tmp_path, edit_profile):
    with TestClient(app) as c:
        hc=login(c)
        uploaded=c.post('/api/sources',headers=hc,files={'file':('private.md',b'# Private\nKEEP_UPLOADED_MARKER','text/markdown')}).json()
        cid=c.post('/api/conversations',headers=hc,json={'title':'Keep me'}).json()['id']
        if edit_profile:
            add(c,hc,'Κράτησε αυτό το χαρακτηριστικό μετά από αναβάθμιση.')
        before=profile.latest()
        db.execute("UPDATE persons SET display_name='CUSTOM_NAME',pw_hash='CUSTOM_HASH' WHERE id='ceo'")
        db.set_setting('demo_fingerprint','older-bundle')
        monkeypatch.setattr('app.main.demo_fingerprint',lambda:'newer-bundle')
        monkeypatch.setattr(db,'reset_all',Mock(side_effect=AssertionError('Automatic reset forbidden')))
        monkeypatch.setattr('app.main.pipeline.ingest_demo',Mock(side_effect=AssertionError('No automatic overwrite')))
        snapshot_dir = tmp_path / 'snapshots'
        snapshot_dir.mkdir()
        source = settings.snapshot_dir / 'ceo.json'
        snapshot = json.loads(source.read_text())
        snapshot['summary'] += ' Updated shipped snapshot.'
        (snapshot_dir / source.name).write_text(json.dumps(snapshot, ensure_ascii=False))
        monkeypatch.setattr(profile, 'settings', dataclasses.replace(settings, snapshot_dir=snapshot_dir))
        bootstrap()
        assert db.one('SELECT id FROM sources WHERE id=?',(uploaded['source_id'],))
        assert db.one('SELECT id FROM conversations WHERE id=?',(cid,))
        assert db.one("SELECT * FROM persons WHERE id='ceo'")['pw_hash']=='CUSTOM_HASH'
        if edit_profile:
            assert profile.latest() == before
        else:
            assert profile.latest()['summary'] == snapshot['summary']
            assert db.one('SELECT id FROM profile_versions WHERE id=?', (before['version'],))
        assert c.get('/api/status',headers=hc).status_code==200


def test_publication_is_opt_in_owner_only_and_tied_to_review():
    with TestClient(app) as c:
        hc=login(c);hs=login(c,'sales_manager','sales2026')
        assert not inherited(c,hs)  # shipped snapshots do not silently count as approval
        tid=add(c,hc)
        assert not inherited(c,hs)
        assert c.post(f'/api/profile/traits/{tid}/publication',headers=hc,json={'published':True}).status_code==400
        assert c.post(f'/api/profile/traits/ceo.{tid}/publication',headers=hs,json={'published':True}).status_code==404
        publish(c,hc,tid)
        assert 'ceo.'+tid in {t['id'] for t in inherited(c,hs)}
        assert all(not t['evidence'] for t in inherited(c,hs))
        assert c.patch(f'/api/profile/traits/ceo.{tid}',headers=hs,json={'action':'edit','text':'overwrite'}).status_code==403
        assert c.post(f'/api/profile/traits/{tid}/publication',headers=hc,json={'published':False}).status_code==200
        assert not inherited(c,hs)


def test_unlabelled_personal_and_model_approved_flags_never_publish():
    with TestClient(app) as c:
        hc=login(c);hs=login(c,'sales_manager','sales2026')
        personal=add(c,hc,'Προσωπικός κανόνας που δεν κοινοποιείται.',scope='personal')
        knowledge=add(c,hc,'Ιδιωτική γνώση που δεν κοινοποιείται.',section='knowledge')
        assert c.post(f'/api/profile/traits/{personal}/publication',headers=hc,json={'published':True,'content_hash':'0'*64}).status_code==400
        assert c.post(f'/api/profile/traits/{knowledge}/publication',headers=hc,json={'published':True,'content_hash':'0'*64}).status_code==404
        with as_person('ceo'):
            p=profile.current()
            p['decision_rules'] += [{'id':'injected-model-rule','rule':'MODEL_ONLY_MARKER','owner_verified':True,
                                     'evidence':[],'published':True,'approved':True,'scope':'company'}]
            p['decision_rules'] += [{'id':'unlabelled','rule':'UNLABELLED_MARKER','owner_verified':True,'evidence':[]}]
            profile.save_version(p,'llm')
        assert not inherited(c,hs)


def test_changed_rule_requires_new_review_and_approval():
    with TestClient(app) as c:
        hc=login(c);hs=login(c,'sales_manager','sales2026');tid=add(c,hc)
        old=review(c,hc,tid);publish(c,hc,tid)
        c.patch(f'/api/profile/traits/{tid}',headers=hc,json={'action':'edit','text':'Νέο όριο με νέα έγκριση.'})
        assert not inherited(c,hs)
        assert c.post(f'/api/profile/traits/{tid}/publication',headers=hc,
                      json={'published':True,'content_hash':old['content_hash']}).status_code==400
        publish(c,hc,tid)
        assert 'ceo.'+tid in {t['id'] for t in inherited(c,hs)}


def test_private_ceo_data_never_reaches_manager_profile_or_model(monkeypatch):
    secret='PRIVATE_CEO_CANARY_482719'
    with TestClient(app) as c:
        hc=login(c);hs=login(c,'sales_manager','sales2026')
        source=c.post('/api/sources',headers=hc,files={'file':('mixed.md',f'# Work\nPilot χωρίς αποκλειστικότητα.\n\n# Private\n{secret}'.encode(),'text/markdown')}).json()
        with as_person('ceo'):
            p=profile.current();p['summary']=secret;p['voice_notes']=[secret];p['unknowns']=[secret]
            p['style']={'channels':{'chat_team':{'greetings':[secret]}}}
            p['graph']={'nodes':[secret]}
            p['knowledge'].append({'id':'private-test','text':secret,'evidence':[],'owner_verified':True})
            profile.save_version(p,'owner-edit')
        tid=add(c,hc);publish(c,hc,tid)
        public=c.get('/api/profile?target=ceo',headers=hs)
        assert secret not in public.text
        assert not public.json()['knowledge'] and not public.json()['style']
        iid=source['source_id']+'-000'
        assert c.get('/api/items/'+iid,headers=hs).status_code==404
        assert secret in c.get('/api/items/'+iid,headers=hc).text
        calls=[]
        def fake(system,user,**kwargs):
            calls.append(system+'\n'+user)
            return {'answer':'Σύμφωνα με τον δημοσιευμένο κανόνα.', 'draft':'Δημοσιευμένος κανόνας.',
                    'choice':0,'trait_refs':[tid],'memory_refs':['M1'],'confidence':0.8}
        monkeypatch.setattr(twin.LLM_CLIENT,'provider','openai')
        monkeypatch.setattr(twin.LLM_CLIENT,'json',fake)
        for path,body in [('/api/twin/ask',{'question':'Εξήγησε την πολιτική για pilot.'}),
                          ('/api/twin/write',{'incoming':'Πρόταση συνεργασίας με pilot.','critique':False}),
                          ('/api/twin/decide',{'situation':'Διάλεξε πλαίσιο pilot.','options':['Μικρό pilot','Μεγάλη δέσμευση']})]:
            r=c.post(path,headers=hs,json={**body,'target':'ceo'})
            assert r.status_code==200,r.text
            assert secret not in r.text and not r.json().get('memories')
        assert len(calls)==3 and all(secret not in payload for payload in calls)
        # Even guessing a known private item/trait ID cannot recover raw evidence.
        v=CURRENT_VIEWER.set('sales')
        try:
            with as_person('ceo'):
                assert twin.exemplars('chat_team','pilot')==[]
                assert twin._nearest_reply('pilot','chat_team')==(None,0.0)
                assert twin._evidence_quote({'evidence':[iid]},'pilot') is None
                assert retrieval.INDEX.search('pilot')==[]
        finally:CURRENT_VIEWER.reset(v)


def test_legacy_history_and_audio_cannot_bypass_new_privacy_rules():
    with TestClient(app) as c:
        hs=login(c,'sales_manager','sales2026')
        cid=c.post('/api/mirrors/ceo/conversations',headers=hs,json={}).json()['conversation_id']
        for role,text in [('user','Old question'),('twin','PRIVATE_OLD_ANSWER')]:
            db.execute('INSERT INTO messages(conversation_id,role,text,payload,created_at) VALUES(?,?,?,?,?)',
                       (int(cid),role,text,'{}',time.time()))
        tid='a'*32
        db.execute('INSERT INTO voice_turns(id,user_id,target,conversation_id,state,audio,created_at) VALUES(?,?,?,?,?,?,?)',
                   (tid,'sales','ceo',int(cid),'READY',b'private old audio',time.time()))
        assert c.get(f'/api/mirrors/ceo/conversations/{cid}',headers=hs).json()==[]
        assert 'PRIVATE_OLD_ANSWER' not in c.get('/api/mirrors/ceo/conversations',headers=hs).text
        assert c.get(f'/api/conversations/{cid}',headers=hs).json()['messages']==[]
        assert c.get(f'/api/voice/{tid}/audio',headers=hs).status_code==403
        assert c.post(f'/api/voice/{tid}/simli',headers=hs,json={'conversation_id':cid}).status_code==403


def test_revocation_blocks_chat_context_audio_and_avatar(monkeypatch):
    with TestClient(app) as c:
        hc=login(c);hs=login(c,'sales_manager','sales2026');tid=add(c,hc);publish(c,hc,tid)
        cid=c.post('/api/mirrors/ceo/conversations',headers=hs,json={}).json()['conversation_id']
        monkeypatch.setattr(voice,'speak',lambda *a:b'RIFF'+b'x'*100)
        a=c.post('/api/mirrors/ceo/spoken-ask',headers=hs,json={'question':'Εξήγησε τον κανόνα pilot.','conversation_id':cid})
        assert a.status_code==200,a.text
        turn=a.json()['turn_id']
        assert c.get(f'/api/voice/{turn}/audio',headers=hs).status_code==200
        c.post(f'/api/profile/traits/{tid}/publication',headers=hc,json={'published':False})
        assert c.get(f'/api/voice/{turn}/audio',headers=hs).status_code==403
        assert c.get(f'/api/voice/{turn}',headers=hs).status_code==403
        assert c.post(f'/api/voice/{turn}/simli',headers=hs,json={'conversation_id':cid}).status_code==403
        assert c.get(f'/api/mirrors/ceo/conversations/{cid}',headers=hs).json()==[]


def test_private_evaluation_and_jobs_are_owner_only():
    with TestClient(app) as c:
        hs=login(c,'sales_manager','sales2026')
        for path in ('/api/eval/latest?target=ceo','/api/blind?target=ceo','/api/blind/stats?target=ceo'):
            assert c.get(path,headers=hs).status_code==403
        assert c.post('/api/eval/run?target=ceo',headers=hs).status_code==403
        jobs._JOBS['secretjob']={'id':'secretjob','person':'ceo','result':'PRIVATE_JOB'}
        assert c.get('/api/jobs/secretjob',headers=hs).status_code==404


def test_explicit_reset_requires_ceo_confirmation_and_creates_backup():
    with TestClient(app) as c:
        hs=login(c,'sales_manager','sales2026');hc=login(c)
        uploaded=c.post('/api/sources',headers=hc,files={'file':('keep.md',b'KEEP_IN_BACKUP_MARKER','text/markdown')}).json()
        assert c.post('/api/reset-demo',headers=hs,json={'confirmation':'RESET_DEMO'}).status_code==403
        assert c.post('/api/reset-demo',headers=hc,json={'confirmation':'wrong'}).status_code==400
        assert db.one('SELECT * FROM sources WHERE id=?',(uploaded['source_id'],))
        r=c.post('/api/reset-demo',headers=hc,json={'confirmation':'RESET_DEMO'})
        assert r.status_code==200
        with sqlite3.connect(db.settings.data_dir/'backups'/r.json()['backup']) as saved:
            assert saved.execute('SELECT id FROM sources WHERE id=?',(uploaded['source_id'],)).fetchone()
        assert not db.one('SELECT * FROM sources WHERE id=?',(uploaded['source_id'],))


def test_existing_database_upgrade_preserves_audio():
    # A database created by the previous schema is upgraded additively.
    db.settings.data_dir.mkdir(exist_ok=True)
    with sqlite3.connect(db.settings.db_path) as old:
        old.executescript(db.SCHEMA)
        old.execute("INSERT INTO voice_turns(id,user_id,target,state,audio,created_at) VALUES('legacy','sales','ceo','READY',?,?)",(b'KEEP_AUDIO',time.time()))
    assert db.one("SELECT audio,access_fingerprint FROM voice_turns WHERE id='legacy'")=={'audio':b'KEEP_AUDIO','access_fingerprint':''}


def test_chat_and_feedback_never_publish_or_train_lower_mirrors():
    with TestClient(app) as c:
        hs=login(c,'sales_manager','sales2026')
        before=db.one('SELECT count(*) n FROM profile_versions')['n']
        assert c.post('/api/mirrors/ceo/ask',headers=hs,json={'question':'Νέος εταιρικός κανόνας: όλα δωρεάν!'}).status_code==200
        c.post('/api/mirrors/ceo/persona-feedback',headers=hs,json={'rating':'faithful'})
        assert db.one('SELECT count(*) n FROM profile_versions')['n']==before
        assert db.one('SELECT count(*) n FROM trait_publications')['n']==0


def test_inherited_identity_does_not_include_private_contact_fields():
    with TestClient(app) as c:
        hc=login(c);hs=login(c,'sales_manager','sales2026')
        row=db.one("SELECT meta FROM persons WHERE id='ceo'")
        row['meta']['emails']=['PRIVATE_CONTACT@example.invalid']
        row['meta']['aliases']=['PRIVATE_ALIAS']
        db.execute("UPDATE persons SET meta=? WHERE id='ceo'",(db.dumps(row['meta']),))
        tid=add(c,hc);publish(c,hc,tid)
        response=c.get('/api/profile',headers=hs)
        assert 'PRIVATE_CONTACT' not in response.text and 'PRIVATE_ALIAS' not in response.text


def test_withdrawn_evidence_invalidates_publication():
    with TestClient(app) as c:
        hc=login(c);hs=login(c,'sales_manager','sales2026')
        source=c.post('/api/sources',headers=hc,files={'file':('evidence.md',b'Pilot policy evidence','text/markdown')}).json()
        tid=add(c,hc)
        with as_person('ceo'):
            p=profile.current()
            next(t for t in p['decision_rules'] if t['id']==tid)['evidence']=[source['source_id']+'-000']
            profile.save_version(p,'owner-edit')
        publish(c,hc,tid)
        assert inherited(c,hs)
        c.patch('/api/sources/'+source['source_id'],headers=hc,json={'consent':False})
        assert not inherited(c,hs)
        c.patch('/api/sources/'+source['source_id'],headers=hc,json={'consent':True})
        assert not inherited(c,hs)


@pytest.mark.parametrize('web', [True,False])
def test_rule_withdrawn_during_generation_is_not_returned_or_spoken(monkeypatch,web):
    with TestClient(app) as c:
        hc=login(c);hs=login(c,'sales_manager','sales2026');tid=add(c,hc);publish(c,hc,tid)
        def fake(*args,**kwargs):
            db.execute("DELETE FROM trait_publications WHERE person_id='ceo'")
            return {'answer':'SHOULD_NOT_RETURN','trait_refs':[tid],'memory_refs':[]}
        monkeypatch.setattr(twin.LLM_CLIENT,'provider','openai')
        monkeypatch.setattr(twin.LLM_CLIENT,'json',fake)
        speech=Mock(side_effect=AssertionError('Revoked response must never reach TTS'))
        monkeypatch.setattr(voice,'speak',speech)
        path='/api/mirrors/ceo/spoken-ask' if web else '/api/twin/ask'
        r=c.post(path,headers=hs,json={'target':'ceo','question':'Εξήγησε τον κανόνα pilot.'})
        assert r.status_code==409 and 'SHOULD_NOT_RETURN' not in r.text
        speech.assert_not_called()


def test_reverting_or_recreating_a_rule_does_not_revive_its_old_approval():
    with TestClient(app) as c:
        hc=login(c);hs=login(c,'sales_manager','sales2026')
        text='ΔΟΚΙΜΑΣΤΙΚΟΣ κανόνας: νέα έγκριση για κάθε αλλαγή.'
        tid=add(c,hc,text);publish(c,hc,tid)
        c.patch(f'/api/profile/traits/{tid}',headers=hc,json={'action':'edit','text':'Αλλαγμένος κανόνας.'})
        c.patch(f'/api/profile/traits/{tid}',headers=hc,json={'action':'edit','text':text})
        assert not inherited(c,hs)
        publish(c,hc,tid)
        c.patch(f'/api/profile/traits/{tid}',headers=hc,json={'action':'delete'})
        new_tid=add(c,hc,text)
        assert new_tid==tid and not inherited(c,hs)
