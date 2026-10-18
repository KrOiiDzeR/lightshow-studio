"""Weekly boundary, precedence, validation and restricted dashboard writes."""
import copy
from datetime import datetime
import unittest
from test_settings import defaults, check_settings, fixture
from lightshow_studio.planning import operation_settings, scheduled_target


def week(**changes):
    return {"id":"week_demo", "enabled":True, "days":[0,2,4], "start":"18:00", "end":"22:00",
            "pack_id":"halloween", "scene_id":"castle", "program_id":"", **changes}


class PlanningTest(unittest.TestCase):
    def setUp(self):
        self.data=defaults()
        self.data['weekly']=[week()]

    def test_old_store_does_not_require_weekly(self):
        self.assertEqual(check_settings(defaults()), defaults())

    def test_weekday_and_exclusive_end_boundary(self):
        for now,expected in [(datetime(2026,10,19,17,59),False),(datetime(2026,10,19,18),True),
                             (datetime(2026,10,19,21,59),True),(datetime(2026,10,19,22),False),
                             (datetime(2026,10,20,19),False)]:
            self.assertEqual(bool(scheduled_target(self.data,now)),expected)

    def test_annual_event_takes_precedence_then_weekly_resumes(self):
        self.data['weekly'][0]['days']=[5]
        self.data['packs'][0]['schedule'].update(enabled=True,month=10,day=31,start='19:00',end='20:00')
        self.assertEqual(scheduled_target(self.data,datetime(2026,10,31,19))[0],'annual:halloween')
        self.assertEqual(scheduled_target(self.data,datetime(2026,10,31,20))[0],'weekly:week_demo')

    def test_weekly_program_target(self):
        program=self.data['packs'][0]['programs'][0]['id']
        self.data['weekly'][0]['program_id']=program
        check_settings(self.data)
        self.assertEqual(scheduled_target(self.data,datetime(2026,10,19,19))[3],program)

    def test_invalid_weekdays_targets_times_and_duplicates_rejected(self):
        for changes in [{'days':[]},{'days':[True]},{'days':[7]},{'days':[0,0]},
                        {'start':'23:00','end':'01:00'},{'pack_id':'missing'},
                        {'scene_id':'missing'},{'program_id':'missing'},{'enabled':1}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                check_settings({**self.data,'weekly':[week(**changes)]})
        with self.assertRaises(ValueError):
            check_settings({**self.data,'weekly':[week(),week()]})

    def test_overlaps_rejected_but_adjacent_or_disabled_allowed(self):
        for second,valid in [(week(id='second',start='21:00',end='23:00'),False),
                             (week(id='second',start='22:00',end='23:00'),True),
                             (week(id='second',days=[1]),True),
                             (week(id='second',enabled=False),True)]:
            candidate={**self.data,'weekly':[week(),second]}
            if valid:check_settings(candidate)
            else:
                with self.assertRaises(ValueError):check_settings(candidate)

    def test_dashboard_merge_preserves_current_lamps_and_scene_changes(self):
        self.data['fixtures']=[fixture('light.my_lamp')]
        self.data['packs'][0]['scenes'][0]['name']='New admin scene'
        original=copy.deepcopy(self.data)
        changed=operation_settings(self.data,{'options':{'shuffle':True}})
        self.assertTrue(changed['options']['shuffle'])
        self.assertEqual(changed['fixtures'],original['fixtures'])
        self.assertEqual(changed['packs'],original['packs'])
        self.assertEqual(self.data,original)

    def test_dashboard_rejects_configuration_and_invalid_controls(self):
        for changes in [{'fixtures':[]},{'packs':[]},{'connection':{}},
                        {'options':{'shuffle':'yes'}},{'options':{'other':True}},
                        {'schedules':{'missing':{}}},{'weekly':[week(days=[])]}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                operation_settings(self.data,changes)
