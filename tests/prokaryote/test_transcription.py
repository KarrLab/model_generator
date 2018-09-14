""" Tests of transcription submodel generation

:Author: Jonathan Karr <karr@mssm.edu>
         Ashwin Srinivasan <ashwins@mit.edu>
:Date: 2018-06-11
:Copyright: 2018, Karr Lab
:License: MIT
"""

import wc_kb_gen
import wc_model_gen.prokaryote as prokaryote
import unittest
import wc_lang
import wc_kb


class TranscriptionSubmodelGeneratorTestCase(unittest.TestCase):
    def test(self):
        kb = wc_kb_gen.random.RandomKbGenerator(options={
            'component': {
                'PropertiesGenerator': {
                    'mean_volume': 1e-15,
                    'mean_cell_cycle_length': 100,
                },
                'GenomeGenerator': {
                    'num_chromosomes': 1,
                    'mean_num_genes': 50,
                    'mean_gene_len': 10,
                    'mean_copy_number': 10,
                    'mean_half_life': 120,
                },
                'MetabolitesGenerator': {
                },
            },
        }).run()

        model = prokaryote.ProkaryoteModelGenerator(
                     knowledge_base=kb,
                     component_generators=[prokaryote.InitalizeModel,
                                           prokaryote.TranscriptionSubmodelGenerator]).run()

        cell = kb.cell
        rnas = cell.species_types.get(__type=wc_kb.prokaryote_schema.RnaSpeciesType)

        submodel = model.submodels.get_one(id='transcription')

        # check compartments generated
        cytosol = model.compartments.get_one(id='c')
        self.assertEqual(cytosol.name, 'Cytosol')

        # check species types and species generated
        for species in kb.cell.species_types.get(__type=wc_kb.prokaryote_schema.RnaSpeciesType):
            model_species = model.species_types.get_one(id=species.id)
            model_species_cytosol = model_species.species.get_one(
                compartment=cytosol)
            self.assertIsInstance(model_species, wc_lang.SpeciesType)
            self.assertIsInstance(model_species_cytosol, wc_lang.Species)

        # check reactions generated
        self.assertEqual(len(submodel.reactions), len(rnas))
        atp = model.species_types.get_one(
            id='atp').species.get_one(compartment=cytosol)
        ctp = model.species_types.get_one(
            id='ctp').species.get_one(compartment=cytosol)
        gtp = model.species_types.get_one(
            id='gtp').species.get_one(compartment=cytosol)
        utp = model.species_types.get_one(
            id='utp').species.get_one(compartment=cytosol)
        ppi = model.species_types.get_one(
            id='ppi').species.get_one(compartment=cytosol)
        h2o = model.species_types.get_one(
            id='h2o').species.get_one(compartment=cytosol)
        h = model.species_types.get_one(
            id='h').species.get_one(compartment=cytosol)
        self.assertEqual(
            + submodel.reactions[0].participants.get_one(species=atp).coefficient
            + submodel.reactions[0].participants.get_one(species=ctp).coefficient
            + submodel.reactions[0].participants.get_one(species=gtp).coefficient
            + submodel.reactions[0].participants.get_one(species=utp).coefficient,
            -rnas[0].get_len())
        self.assertEqual(
            + submodel.reactions[0].participants.get_one(species=ppi).coefficient,
            rnas[0].get_len())
        self.assertEqual(
            + submodel.reactions[0].participants.get_one(species=h2o).coefficient,
            rnas[0].get_len() - 1)
        self.assertEqual(
            + submodel.reactions[0].participants.get_one(species=h).coefficient,
            -(rnas[0].get_len() - 1))

        """ rna_poly = model.observables.get_one(
            id='rna_poly_obs')
        # http://bionumbers.hms.harvard.edu/bionumber.aspx?s=n&v=2&id=106199
        poly_avg_conc = 3000/scipy.constants.Avogadro / cytosol.initial_volume
        # check rate laws
        for rxn in submodel.reactions:
            self.assertEqual(len(rxn.rate_laws), 1)
            rl = rxn.rate_laws[0]
            self.assertEqual(rl.direction.name, 'forward')
            numpy.testing.assert_equal(rl.k_m, poly_avg_conc)
"""
