import biosteam as bst
import thermosteam as tmo

# Calculation of the feedstock flow
MeOH_kg_hr = 2083.3          
FE_MeOH = 0.128              
FE_H2 = 0.259                
FE_CO = 0.644                
SPC = 0.21                   
w_MeOH = 0.06                
KOH_M = 1.0                  

n_MeOH = MeOH_kg_hr / 32.04                 
n_e = n_MeOH * 6 / FE_MeOH                 
n_H2 = n_e * FE_H2 / 2                      
n_CO = n_e * FE_CO / 2                     

n_CO2_converted = n_MeOH + n_CO             
n_CO2_in = n_CO2_converted / SPC            
n_CO2_unreacted = n_CO2_in - n_CO2_converted
n_CO2_carbonate = n_e / 2                   
n_CO2_out = n_CO2_unreacted - n_CO2_carbonate   

water_kg_hr = MeOH_kg_hr * (1 - w_MeOH) / w_MeOH   
n_KOH = KOH_M * water_kg_hr / 1000          
n_K2CO3 = n_KOH / 2                        

print(f"MeOH {n_MeOH:.2f}  H2 {n_H2:.1f}  CO {n_CO:.1f}  kmol/h")
print(f"CO2: in {n_CO2_in:.1f}, conversiopn {n_CO2_converted:.1f},"
      f"Carbonate {n_CO2_carbonate:.1f}, out {n_CO2_out:.1f} kmol/h")
print(f"Carbonate loss as a fraction of unreacted CO2 {n_CO2_carbonate / n_CO2_unreacted:.1%}")
print(f"H2O {water_kg_hr:.0f} kg/h, K2CO3 {n_K2CO3:.2f} kmol/h")

# Define the fddestock flow
water    = tmo.Chemical('Water')
methanol = tmo.Chemical('Methanol')
co2      = tmo.Chemical('CO2')
co       = tmo.Chemical('CO')
h2       = tmo.Chemical('H2')

co2.at_state('g')               
co.at_state('g')                
h2.at_state('g')            


k2co3 = tmo.Chemical('K2CO3')   
k2co3.at_state('l')             
k2co3.default()                 
bst.settings.set_thermo([water, methanol, co2, co, h2, k2co3])

# Feeedsock of the material
feed = bst.Stream(
    'cathode_effluent',
    Methanol=n_MeOH,
    CO2=n_CO2_out,
    CO=n_CO,
    H2=n_H2,
    K2CO3=n_K2CO3,
    units='kmol/hr',
    T=298.15,                   
    P=101325,                   
    phase='l',
)
feed.imass['Water'] = water_kg_hr   

feed.show(flow='kmol/hr')
print(f"Mass fraction of methanol in the liquid (excluding gases and salts):"
      f"{feed.imass['Methanol'] / (feed.imass['Methanol'] + feed.imass['Water']):.2%}")
