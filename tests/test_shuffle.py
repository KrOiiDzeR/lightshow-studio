"""Validate fixed per-area pools and preserve legacy current-pack behavior."""
import copy
from unittest import TestCase
from test_settings import defaults, check_settings
from lightshow_studio.planning import operation_settings
from lightshow_studio.shuffle import shuffle_candidates


class ShuffleSelectionTest(TestCase):
    def test_legacy_settings_keep_current_pack(self):
        data=defaults()
        self.assertNotIn('shuffle_scenes',check_settings(data))
        choices=shuffle_candidates(data,'halloween','castle')
        self.assertTrue(choices)
        self.assertTrue(all(pack=='halloween' and scene!='castle' for pack,scene in choices))

    def test_cross_pack_selection_and_no_immediate_repeat(self):
        data=defaults()
        data['shuffle_scenes']=[{'pack_id':'halloween','scene_id':'castle'},
                                {'pack_id':'ambience','scene_id':'summer'}]
        check_settings(data)
        self.assertEqual(shuffle_candidates(data,'halloween','castle'),[('ambience','summer')])
        self.assertEqual(shuffle_candidates(data,'ambience','summer'),[('halloween','castle')])

    def test_explicit_empty_or_single_current_scene_never_falls_back(self):
        data=defaults();data['shuffle_scenes']=[]
        self.assertEqual(shuffle_candidates(check_settings(data),'halloween','castle'),[])
        data['shuffle_scenes']=[{'pack_id':'halloween','scene_id':'castle'}]
        self.assertEqual(shuffle_candidates(data,'halloween','castle'),[])

    def test_invalid_and_duplicate_references_rejected(self):
        row={'pack_id':'halloween','scene_id':'castle'}
        for pool in [None,{},[row,row],[{'pack_id':'missing','scene_id':'castle'}],
                     [{'pack_id':'halloween','scene_id':'missing'}],[{'scene_id':'castle'}],
                     [{**row,'extra':True}],[{'pack_id':[],'scene_id':'castle'}]]:
            with self.subTest(pool=pool),self.assertRaises(ValueError):
                check_settings({**defaults(),'shuffle_scenes':pool})

    def test_dashboard_cannot_overwrite_configured_selection(self):
        data=defaults();data['shuffle_scenes']=[{'pack_id':'ambience','scene_id':'summer'}]
        original=copy.deepcopy(data)
        result=operation_settings(data,{'options':{'shuffle':True}})
        self.assertEqual(result['shuffle_scenes'],original['shuffle_scenes'])
        self.assertEqual(data,original)
        with self.assertRaises(ValueError):operation_settings(data,{'shuffle_scenes':[]})
