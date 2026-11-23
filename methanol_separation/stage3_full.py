import warnings
from pathlib import Path
import biosteam as bst
import thermosteam as tmo

warnings.filterwarnings('ignore', category=bst.exceptions.CostWarning)   # equipment-cost warnings are irrelevant (no TEA)

from stage1_feed import feed


T_flash = 298.15          
P_atm = 101325            
T_gas_cool = 278.15           
wash_water_ratio = 0.1     
PSA_split = {'CO2': 0.90, 'CO': 0.05, 'H2': 0.02}   
MeOH_purity_wt = 0.9985    
MeOH_recovery = 0.995      
k_reflux = 1.25            
T_cond = 303.15          
T_elec = 303.15           



# F101: gas-liquid separator 
F101 = bst.Flash(
    'F101',
    ins = feed,
    outs = ('F101_vapor', 'F101_liquid'),
    T = T_flash,
    P = P_atm,
)

# 2. Gas line: H101 -> U102 -> U101
H101 = bst.HXutility(
    'H101',
    ins = F101-0,                 
    outs = ('H101_out',),
    T = T_gas_cool,
    rigorous = True,           
)

wash_water = bst.Stream('wash_water', Water=1, units='kg/hr', T=T_gas_cool, P=P_atm)   

U102 = bst.VentScrubber(
    'U102',
    ins = (wash_water, H101-0),   
    outs = ('U102_gas', 'U102_liquid'),   
    gas = ('CO2', 'CO', 'H2'), 
)

@U102.add_specification(run=True)
def set_wash_water():
    """Before U102 runs, set wash water = ratio x mass of the GAS part of the inlet."""
    gas_in = U102.ins[1]
    gas_mass = gas_in['g'].F_mass if len(gas_in.phases) > 1 else gas_in.F_mass
    U102.ins[0].imass['Water'] = wash_water_ratio * gas_mass

U101 = bst.Splitter(        
    'U101',
    ins = U102-0,                 
    outs = ('CO2_recycle', 'off_gas'),
    split = PSA_split,        
)


# 3. Liquid line: M102 -> D101
M102 = bst.Mixer(
    'M102',
    ins = (F101-1, U102-1),          
    outs = ('column_feed',),
)

# Mole fraction of methanol on a methanol + water basis.
MW_MeOH, MW_water = 32.04, 18.015
y_top = (MeOH_purity_wt / MW_MeOH) / (MeOH_purity_wt / MW_MeOH + (1 - MeOH_purity_wt) / MW_water)

D101 = bst.BinaryDistillation(
    'D101',
    ins = M102-0,                 
    outs = ('D101_overhead', 'D101_bottoms'),   
    LHK = ('Methanol', 'Water'),          
    y_top = y_top,
    x_bot = 1e-6,              
    k = k_reflux,
    P = P_atm,
    partial_condenser = True,  
    product_specification_format = 'Composition',
)

@D101.add_specification(run=True)
def set_x_bot():
    """Convert the methanol recovery target into the bottoms mole fraction x_bot."""
    f = D101.ins[0]
    top_MeOH = f.imol['Methanol'] * MeOH_recovery
    top_water = top_MeOH * (1 - y_top) / y_top
    bot_MeOH = f.imol['Methanol'] - top_MeOH
    bot_water = f.imol['Water'] - top_water
    D101.x_bot = bot_MeOH / (bot_MeOH + bot_water)


# 4. Column overhead: H102 -> F103
H102 = bst.HXutility(
    'H102',
    ins = D101-0,                
    outs = ('H102_out',),
    T = T_cond,
    rigorous = True,
)

F103 = bst.Flash(
    'F103',
    ins=H102-0,
    outs=('column_vent', 'methanol'),   
    T = T_cond,                   
    P = P_atm,
)


# 5. Column bottoms: H103
H103 = bst.HXutility(
    'H103',
    ins = D101-1,                 
    outs = ('electrolyte_return',),
    T = T_elec,
)

# 6. Build system from all units and simulate it
sep_sys = bst.main_flowsheet.create_system('sep_sys')   
sep_sys.simulate()                                          

print('[CHECK] Calculation order:', [u.ID for u in sep_sys.units])   

# 7. Results
product = F103.outs[1]
feed_MeOH = feed.imass['Methanol']           

purity = product.imass['Methanol'] / product.F_mass
recovery = product.imass['Methanol'] / feed.imass['Methanol']                         
loss_off_gas = U101.outs[1].imass['Methanol'] / feed_MeOH
loss_vent = F103.outs[0].imass['Methanol'] / feed_MeOH
to_electrolyte = H103.outs[0].imass['Methanol'] / feed_MeOH
  

print(f"Methanol purity          = {purity:.4%}")
print(f"Methanol recovery        = {recovery:.2%}")
print(f"Wash water               = {wash_water.F_mass:,.0f} kg/h")
print(f"Theoretical stages       = {D101.design_results['Theoretical stages']}")
print(f"[CHECK] MeOH lost in off-gas       = {loss_off_gas:.2%}")      
print(f"[CHECK] MeOH lost in column vent   = {loss_vent:.2%}")         
print(f"[CHECK] MeOH back with electrolyte = {to_electrolyte:.2%}")    
print(f"[CHECK] Salt in product (kg/h)     = {product.imass['K2CO3']:.3g}")   

# 8. BioSTEAM diagram 
bst.preferences.light_mode()
sep_sys.diagram(kind = 'thorough', number = True, label = True,
                file = str(Path(__file__).parent / 'stage3_diagram'), format='png', display = False)
