""" Tests for macromolecular complexation submodel generator

:Author: Yin Hoon Chew <yinhoon.chew@mssm.edu>
:Date: 2019-08-02
:Copyright: 2019, Karr Lab
:License: MIT
"""

from wc_model_gen.eukaryote import complexation
from wc_onto import onto as wc_ontology
from wc_utils.util.units import unit_registry
import os
import scipy.constants
import shutil
import tempfile
import unittest
import wc_lang
import wc_kb


class TestCase(unittest.TestCase):

    def setUp(self):

        # Create KB content
        self.tmp_dirname = tempfile.mkdtemp()
        self.sequence_path = os.path.join(self.tmp_dirname, 'test_seq.fasta')
        with open(self.sequence_path, 'w') as f:
            f.write('>chr1\nGCGTGCGATGAT\n')

        self.kb = wc_kb.KnowledgeBase()
        cell = self.kb.cell = wc_kb.Cell()

        nucleus = cell.compartments.create(id='n')
        mito = cell.compartments.create(id='m')

        chr1 = wc_kb.core.DnaSpeciesType(cell=cell, id='chr1', sequence_path=self.sequence_path)
        gene1 = wc_kb.eukaryote.GeneLocus(cell=cell, id='gene1', polymer=chr1, start=1, end=12)
        
        locus1 = wc_kb.eukaryote.GenericLocus(start=1, end=6)
        transcript1 = wc_kb.eukaryote.TranscriptSpeciesType(cell=cell, gene=gene1, exons=[locus1])
        prot1 = wc_kb.eukaryote.ProteinSpeciesType(cell=cell, id='prot1', transcript=transcript1, coding_regions=[locus1])
        prot1_half_life = wc_kb.core.SpeciesTypeProperty(property='half_life', species_type=prot1, 
            value='40000.0', value_type=wc_ontology['WC:float'])
        prot1_spec = wc_kb.core.Species(species_type=prot1, compartment=nucleus)
        
        locus2 = wc_kb.eukaryote.GenericLocus(start=4, end=9)
        transcript2 = wc_kb.eukaryote.TranscriptSpeciesType(cell=cell, gene=gene1, exons=[locus2])
        prot2 = wc_kb.eukaryote.ProteinSpeciesType(cell=cell, id='prot2', transcript=transcript2, coding_regions=[locus2])
        prot2_half_life = wc_kb.core.SpeciesTypeProperty(property='half_life', species_type=prot2, 
            value='20000.0', value_type=wc_ontology['WC:float'])
        prot2_spec = wc_kb.core.Species(species_type=prot2, compartment=nucleus)
        
        locus3 = wc_kb.eukaryote.GenericLocus(start=7, end=12)
        transcript3 = wc_kb.eukaryote.TranscriptSpeciesType(cell=cell, gene=gene1, exons=[locus3])
        prot3 = wc_kb.eukaryote.ProteinSpeciesType(cell=cell, id='prot3', transcript=transcript3, coding_regions=[locus3])
        prot3_half_life = wc_kb.core.SpeciesTypeProperty(property='half_life', species_type=prot3, 
            value='25000.0', value_type=wc_ontology['WC:float'])
        prot3_spec1 = wc_kb.core.Species(species_type=prot3, compartment=nucleus)
        prot3_spec2 = wc_kb.core.Species(species_type=prot3, compartment=mito)
        
        complex1 = wc_kb.core.ComplexSpeciesType(cell=cell, id='complex1', subunits=[
            wc_kb.core.SpeciesTypeCoefficient(species_type=prot1, coefficient=1),
            wc_kb.core.SpeciesTypeCoefficient(species_type=prot2, coefficient=2),
            wc_kb.core.SpeciesTypeCoefficient(species_type=prot3, coefficient=0),
            ])        

        # Create initial model content
        self.model = model = wc_lang.Model()
        
        model.parameters.create(id='Avogadro', value = scipy.constants.Avogadro,
                                units = unit_registry.parse_units('molecule mol^-1'))

        compartments = {'n': ('nucleus', 5E-14), 'm': ('mitochondria', 2.5E-14)}
        for k, v in compartments.items():
            init_volume = wc_lang.core.InitVolume(distribution=wc_ontology['WC:normal_distribution'], 
                    mean=v[1], std=0)
            c = model.compartments.create(id=k, name=v[0], init_volume=init_volume)
            c.init_density = model.parameters.create(id='density_' + k, value=1000, 
                units=unit_registry.parse_units('g l^-1'))
            volume = model.functions.create(id='volume_' + k, units=unit_registry.parse_units('l'))
            volume.expression, error = wc_lang.FunctionExpression.deserialize(f'{c.id} / {c.init_density.id}', {
                wc_lang.Compartment: {c.id: c},
                wc_lang.Parameter: {c.init_density.id: c.init_density},
                })
            assert error is None, str(error)

        for i in cell.species_types.get(__type=wc_kb.eukaryote.ProteinSpeciesType):
            model_species_type = model.species_types.get_or_create(id=i.id)
            model_compartment = model.compartments.get_one(id='n')
            model_species = model.species.get_or_create(species_type=model_species_type, compartment=model_compartment)
            model_species.id = model_species.gen_id()
            conc_model = model.distribution_init_concentrations.get_or_create(species=model_species, 
                mean=10, units=unit_registry.parse_units('molecule'))
            conc_model.id = conc_model.gen_id()

        model_species_type = model.species_types.get_or_create(id='prot3')
        model_mito = model.compartments.get_one(id='m')
        model_species = model.species.get_or_create(species_type=model_species_type, compartment=model_mito)
        model_species.id = model_species.gen_id()
        conc_model = model.distribution_init_concentrations.create(species=model_species, 
            mean=20, units=unit_registry.parse_units('molecule'))
        conc_model.id = conc_model.gen_id()

        model_species_type = model.species_types.create(id=complex1.id)
        subunit_compartments = [[s.compartment.id for s in sub.species_type.species]
            for sub in complex1.subunits]
        shared_compartments = set([])
        for i in range(len(subunit_compartments)):
            shared_compartments = (set(subunit_compartments[i])
                if i==0 else shared_compartments).intersection(
                set(subunit_compartments[i+1]) if i<(len(subunit_compartments)-1) else shared_compartments)            
        compartment_ids = set(list(shared_compartments))
        for compartment_id in compartment_ids:
            model_compartment = model.compartments.get_one(id=compartment_id)
            model_species = model.species.get_or_create(species_type=model_species_type, compartment=model_compartment)
            model_species.id = model_species.gen_id()

        metabolic_participants = ['Ala', 'Cys', 'Asp', 'Glu', 'h2o']
        for i in metabolic_participants:
            model_species_type = model.species_types.create(id=i)            
            model_compartment = model.compartments.get_one(id='n')
            model_species = model.species.create(species_type=model_species_type, compartment=model_compartment)
            model_species.id = model_species.gen_id()
            
    def tearDown(self):
        shutil.rmtree(self.tmp_dirname)                     

    def test_methods(self):

        model = self.model

        amino_acid_id_conversion = {
            'A': 'Ala',
            'C': 'Cys',
            'D': 'Asp',
            }
        gen = complexation.ComplexationSubmodelGenerator(self.kb, self.model, options={
            'amino_acid_id_conversion': amino_acid_id_conversion,
            'cds': False,                
            })
        gen.run()   

        self.assertEqual(len(model.reactions), 4)
        self.assertEqual([i.id for i in model.submodels], ['complexation'])

        # Test gen_reaction
        complex_assembly = model.reactions.get_one(id='complex_association_complex1_n')
        self.assertEqual(complex_assembly.name, 'Complexation of complex1 in nucleus')
        self.assertEqual(complex_assembly.reversible, False)
        self.assertEqual(complex_assembly.comments, '')
        self.assertEqual([(i.species.id, i.coefficient) for i in complex_assembly.participants],
            [('prot1[n]', -1), ('prot2[n]', -2), ('prot3[n]', -1), ('complex1[n]', 1)])
        
        dissociate_prot1 = model.reactions.get_one(id='complex1_n_dissociation_prot1_degradation')
        self.assertEqual(dissociate_prot1.name, 'Dissociation of complex1 and degradation of prot1 in nucleus')
        self.assertEqual(dissociate_prot1.reversible, False)
        self.assertEqual(dissociate_prot1.comments, '')
        self.assertEqual(sorted([(i.species.id, i.coefficient) for i in dissociate_prot1.participants]),
            sorted([('complex1[n]', -1), ('h2o[n]', -1), ('Ala[n]', 1), ('Cys[n]', 1), ('prot2[n]', 2), ('prot3[n]', 1)]))
        
        dissociate_prot2 = model.reactions.get_one(id='complex1_n_dissociation_prot2_degradation')
        self.assertEqual(sorted([(i.species.id, i.coefficient) for i in dissociate_prot2.participants]),
            sorted([('complex1[n]', -1), ('h2o[n]', -1), ('Cys[n]', 1), ('Asp[n]', 1), ('prot1[n]', 1), ('prot2[n]', 1), ('prot3[n]', 1)]))

        dissociate_prot3 = model.reactions.get_one(id='complex1_n_dissociation_prot3_degradation')
        self.assertEqual(sorted([(i.species.id, i.coefficient) for i in dissociate_prot3.participants]),
            sorted([('complex1[n]', -1), ('h2o[n]', -1), ('Asp[n]', 2), ('prot1[n]', 1), ('prot2[n]', 2)]))


        # Test gen_rate_laws
        self.assertEqual(complex_assembly.rate_laws[0].expression.expression, 
            'k_cat_complex_association_complex1_n * '
            '(prot1[n] / (prot1[n] + K_m_complex_association_complex1_n_prot1 * Avogadro * volume_n)) * '
            '(prot2[n] / (prot2[n] + K_m_complex_association_complex1_n_prot2 * Avogadro * volume_n)) * '
            '(prot3[n] / (prot3[n] + K_m_complex_association_complex1_n_prot3 * Avogadro * volume_n))')
        self.assertEqual(complex_assembly.rate_laws[0].direction, wc_lang.RateLawDirection.forward)
        self.assertEqual(dissociate_prot1.rate_laws[0].expression.expression, 
            'k_cat_complex1_n_dissociation_prot1_degradation * complex1[n]')
        self.assertEqual(dissociate_prot3.rate_laws[0].expression.expression, 
            'k_cat_complex1_n_dissociation_prot3_degradation * complex1[n]')

        # Test calibrate_submodels
        self.assertEqual(model.parameters.get_one(id='K_m_complex_association_complex1_n_prot1').value, 10/scipy.constants.Avogadro/5E-14)
        self.assertEqual(model.parameters.get_one(id='K_m_complex_association_complex1_n_prot3').value, 10/scipy.constants.Avogadro/5E-14)
        self.assertEqual(model.parameters.get_one(id='k_cat_complex_association_complex1_n').value, 2e06)
        self.assertEqual(model.parameters.get_one(id='k_cat_complex_association_complex1_n').comments, 
            'The rate constant for bimolecular protein-protein association was used '
            'so that the simulated rate of complex assembly will be within the higher range')
        self.assertEqual(model.parameters.get_one(id='k_cat_complex_association_complex1_n').references[0].title, 
            'Kinetics of protein-protein association explained by Brownian dynamics computer simulation')
        self.assertEqual(model.parameters.get_one(id='k_cat_complex1_n_dissociation_prot1_degradation').value, 1/40000.)
        self.assertEqual(model.parameters.get_one(id='k_cat_complex1_n_dissociation_prot2_degradation').value, 2/20000.)
        self.assertEqual(model.parameters.get_one(id='k_cat_complex1_n_dissociation_prot3_degradation').value, 1/25000.)