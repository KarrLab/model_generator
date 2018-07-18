""" Generator for protein  degradation submodels based on KBs for random in silico organisms

:Author: Bilal Shaikh <bilal.shaikh@columbia.edu>
         Jonathan Karr <karr@mssm.edu>
:Date: 2018-07-05
:Copyright: 2018, Karr Lab
:License: MIT
"""
import numpy
import scipy
import wc_kb
import wc_lang
import wc_model_gen


class ProteinDegradationSubmodelGenerator(wc_model_gen.SubmodelGenerator):
    """ Gnerator for Protein degradation model"""

    def gen_compartments(self):
        self.cell = self.knowledge_base.cell
        model = self.model
        cytosol = model.compartments.get_or_create(id='c')
        cytosol.name = 'cytosol'
        cytosol.initial_volume = self.cell.properties.get_one(
            id='mean_volume').value

    def gen_species(self):
        "Generate the protein species for the model"

        cell = self.knowledge_base.cell
        model = self.model
        cytosol = model.compartments.get_or_create(id='c')

        proteins = cell.species_types.get(__type=wc_kb.ProteinSpeciesType)
        for protein in proteins:
            species_type = model.species_types.get_or_create(id=protein.id)
            if not species_type.name:
                species_type.name = protein.name
                species_type.type = wc_lang.SpeciesTypeType.protein
                species_type.structure = protein.get_seq()
                species_type.empirical_formula = protein.get_empirical_formula()
                species_type.molecular_weight = protein.get_mol_wt()
                species_type.charge = protein.get_charge()
                species = species_type.species.get_or_create(
                    compartment=cytosol)
                print("hello")
                print(type(species))
                print(species)

                species.concentration = wc_lang.Concentration(
                    value=protein.concentration, units=wc_lang.ConcentrationUnit.M)

    def gen_reactions(self):

        model = self.model
        submodel = self.submodel
        cytosol = model.compartments.get_one(id='c')

        proteins = self.cell.species_types.get(
            __type=wc_kb.core.ProteinSpeciesType)

        for kb_protein in proteins:
            if kb_protein.id.startswith('protein_'):
                rxn = submodel.reactions.get_or_create(
                    id=kb_protein.id.replace('protein', 'protein_degradation_'))
                rxn.name = kb_protein.name.replace(
                    'protein ', 'protein degradation ')
            else:
                rxn = submodel.reactions.get_or_create(
                    id='protein_degradation_'+str(kb_protein.id))
                rxn.name = 'protein degradation '+str(kb_protein.name)

            model_protein = model.species_types.get_one(
                id=kb_protein.id).species.get_one(compartment=cytosol)
            print(model_protein)
            seq = kb_protein.get_seq()

            rxn.participants = []

            # The protein being degraded
            rxn.participants.add(
                model_protein.species_coefficients.get_or_create(coefficient=-1))

            # ATP used to attach protein to proteosome
            atp = model.species_types.get_one(
                id='atp').species.get_one(compartment=cytosol)
            adp = model.species_types.get_one(
                id='adp').species.get_one(compartment=cytosol)
            pi = model.species_types.get_one(
                id='pi').species.get_one(compartment=cytosol)
            rxn.participants.add(
                atp.species_coefficients.get_or_create(coefficient=-1))
            rxn.participants.add(
                adp.species_coefficients.get_or_create(coefficient=1))
            rxn.participants.add(
                pi.species_coefficients.get_or_create(coefficient=1))

            # Water needed for the seperation of each amino acid
            h2o = model.species_types.get_one(
                id='h2o').species.get_one(compartment=cytosol)

            rxn.participants.add(
                h2o.species_coefficients.get_or_create(coefficient=-len(seq)))

            # The 20 amino acids
            amino_acids = ['ala', 'arg', 'asp', 'asn', 'cys', 'gln', 'glu', 'gly', 'his',
                           'ile', 'leu', 'lys', 'met', 'phe', 'pro', 'ser', 'thr', 'trp', 'tyr', 'val']
            aas = ["A", "R", "N", "D", "C", "Q", "E", "G", "H", "I",
                   "L", "K", "M", "F", "P", "S", "T", "W", "Y", "V"]

            for amino_acid, aa in zip(amino_acids, aas):
                species = model.species_types.get_one(
                    id=amino_acid).species_types.get_one(compartment=cytosol)
                rxn.participants.add(
                    aa.species_coefficients.get_or_create(coefficient=seq.count(aa)))

    def gen_rate_laws(self):
        model = self.model
        cell = self.knowledge_base.cell
        cytosol = self.cytosol

        prots = cell.species_types.get(__type=wc_kb.ProteinSpeciesType)
        for prot, rxn in zip(prots, self.submodel.reactions):
            rl = rxn.rate_laws.create()
            rl.direction = wc_lang.RateLawDirection.forward
            rl.equation = wc_lang.RateLawEquation(
                expression='k_cat * {0}[c] / (k_m + {0}[c])'.format(prot.id))
            rl.k_cat = 2 * numpy.log(2) / prot.half_life
            rl.k_m = prot.concentration
            rl.equation.modifiers.append(rxn.participants[0].species)
