""" Tests for utility methods

:Author: Yin Hoon Chew <yinhoon.chew@mssm.edu>
:Date: 2019-02-13
:Copyright: 2019, Karr Lab
:License: MIT
"""

from wc_utils.util.ontology import wcm_ontology
from wc_utils.util.units import unit_registry
import wc_model_gen.utils as utils
import math
import unittest
import wc_lang


class TestCase(unittest.TestCase):

    def test_calculate_average_synthesis_rate(self):

        test_rate = utils.calculate_average_synthesis_rate(0.5, 300., 36000.)
        self.assertAlmostEqual(test_rate, 0.001164872, places=9)

    def test_MM_like_rate_law(self):

        Avogadro = wc_lang.Parameter(id='Avogadro')
		
        c = wc_lang.Compartment(id='c')
        c.init_density = wc_lang.Parameter(id='density_' + c.id)                
        volume = wc_lang.Function(id='volume_' + c.id)
        volume.expression, error = wc_lang.FunctionExpression.deserialize(f'{c.id} / {c.init_density.id}', {
                wc_lang.Compartment: {c.id: c},
                wc_lang.Parameter: {c.init_density.id: c.init_density},
                })
		
        species_types = {}
        species = {}
        for i in range(1,6):
            Id = 's' + str(i)
            species_types[Id] = wc_lang.SpeciesType(id=Id)
            species[Id + '_c'] = wc_lang.Species(species_type=species_types[Id], compartment=c)
            wc_lang.DistributionInitConcentration(species=species[Id + '_c'], mean=0.5)

        ob = wc_lang.ObservableExpression(expression='s4[c] + s5[c]', species=[species['s4_c'], species['s5_c']])
        modifier = wc_lang.Observable(id='e1', expression=ob)
	        
        participant1 = wc_lang.SpeciesCoefficient(species=species['s1_c'], coefficient=-1)
        participant2 = wc_lang.SpeciesCoefficient(species=species['s2_c'], coefficient=-1)
        participant3 = wc_lang.SpeciesCoefficient(species=species['s3_c'], coefficient=1)
        reaction = wc_lang.Reaction(id='r1', participants=[participant1, participant2, participant3])

        rate_law, parameters = utils.MM_like_rate_law(Avogadro, reaction, modifier, 1.)

        self.assertEqual(rate_law.expression, 'k_cat_r1 * e1 * (s1[c] / (s1[c] + K_m_r1_s1 * Avogadro * volume_c)) * (s2[c] / (s2[c] + K_m_r1_s2 * Avogadro * volume_c))')
        self.assertEqual(set([i.gen_id() for i in rate_law.species]), set(['s1[c]', 's2[c]']))
        self.assertEqual(rate_law.observables, [modifier])
        self.assertEqual(set(rate_law.parameters), set(parameters))        
        self.assertEqual(rate_law.parameters.get_one(id='k_cat_r1').type, wcm_ontology['WCM:k_cat'])
        self.assertEqual(rate_law.parameters.get_one(id='k_cat_r1').units, unit_registry.parse_units('s^-1'))
        self.assertEqual(rate_law.parameters.get_one(id='K_m_r1_s2').type, wcm_ontology['WCM:K_m'])
        self.assertEqual(rate_law.parameters.get_one(id='K_m_r1_s2').value, 0.5)
        self.assertEqual(rate_law.parameters.get_one(id='K_m_r1_s2').units, unit_registry.parse_units('M'))
