""" Plots the SED of all latitude stripes necessary to observe the Fermi bubbles. """

import numpy as np
import pyfits
import healpy
from matplotlib import pyplot
import healpylib as hlib
from iminuit import Minuit

import dio
from yaml import load

########################################################################################################################## Parameters

input_data = 'data'  # data, lowE, boxes, GALPROP
plot_diff_leftright = True

fit_plaw = False
fit_plaw_cut = True

bin_start_fit = 5 # Energy bin where fit starts (is halved if combine_two_energy_bins)
binmin = 2
binmax = 20

fn_ending = '.pdf'
colours = ['blue', 'red']


########################################################################################################################## Constants

dL = 10.
dB = [10., 10., 10., 10., 10., 4., 4., 4., 4., 4., 10., 10., 10., 10., 10.]

GeV2MeV = 1000.
delta = 0.346573590092441 # logarithmic distance between two energy bins
plot_dir = '../plots/'

########################################################################################################################## Load dictionaries

dct  = dio.loaddict('../dct/dct_' + input_data + '.yaml')

Lc = dct['3) Center_of_lon_bins']
Bc = dct['4) Center_of_lat_bins']

Es = np.asarray(dct['5) Energy_bins'])
diff_profiles = dct['6) Differential_flux_profiles']
std_profiles = dct['7) Standard_deviation_profiles']

nB = len(diff_profiles)
nL = len(diff_profiles[0])
nE = len(diff_profiles[0][0])
print 'nB, nL, nE = ' + str(nB) + ', ' + str(nL) + ', ' + str(nE)

########################################################################################################################## Define powerlaw classes

if fit_plaw: # with chi2 fit with 2 free parameters: spectral index and normalization]
    class PowerLawChi2:
        def __init__(self,x,y,sigma, E_zero):
            self.x = x
            self.y = y
            self.sigma = sigma
            self.E_zero = E_zero
        def __call__(self, N_zero, Gamma): 
            chi2 = sum((y - N_zero * (x/E_zero)**(-Gamma))**2 / sigma**2 for x,y,sigma in zip(self.x, self.y, self.sigma))
            return chi2

if fit_plaw_cut:
    class PlawCutChi2:
        def __init__(self,x,y,sigma, E_zero):
            self.x = x
            self.y = y
            self.sigma = sigma
            self.E_zero = E_zero
        def __call__(self, N_zero, Gamma, E_cut): 
            chi2 = sum((y - N_zero * (x/E_zero)**(-Gamma) * np.exp(-x/E_cut))**2/ sigma**2 for x,y,sigma in zip(self.x, self.y, self.sigma))
            print chi2
            return chi2


########################################################################################################################## Plot profiles

E_zero = Es[bin_start_fit]

for b in xrange(nB):
    print Bc[b]
    pyplot.figure()
    colour_index = 0
    for l in xrange(nL):
        map  = np.asarray(diff_profiles[b][l])
        std_map = np.asarray(std_profiles[b][l])

        for E in xrange(nE):
            if std_map[E] < 10.e-30:
                std_map[E] = 10.e-7

        label = r'$\ell \in (%i^\circ$' % (Lc[l] - dL/2) + r', $%i^\circ)$' % (Lc[l] + dL/2)
        pyplot.errorbar(Es, map, std_map, color=colours[colour_index], marker='s', markersize=4, markeredgewidth=0.4, linestyle = '', linewidth=0.1, label=label)


########################################################################################################################## Fit powerlaw


        if fit_plaw:
        
            chi2 = PowerLawChi2(Es[binmin:binmax], map[binmin:binmax], std_map[binmin:binmax], E_zero)
            N_zero =  int(len(map)/2)
            print N_zero
            print E_zero
            m = Minuit(chi2, N_zero = N_zero, error_N_zero = 0.00001, Gamma = 0.4, error_Gamma = 0.1, errordef = 1.)
            m.migrad()
            Gamma = m.values['Gamma'] # Spectral index
            N_zero = m.values['N_zero']

            pyplot.errorbar(Es[binmin:binmax], [N_zero * (x / E_zero)**(-Gamma) for x in Es[binmin:binmax]], label = r'$\gamma = $%.2f' %Gamma, color = colours[colour_index])
                
            chi2_value = sum((map[binmin:binmax] - N_zero * (Es[binmin:binmax]/E_zero)**(-Gamma))**2 / std_map[binmin:binmax]**2)
            dof = binmax - binmin - 2

            
        if fit_plaw_cut:
            chi2 = PlawCutChi2(Es[binmin:binmax], map[binmin:binmax], std_map[binmin:binmax], E_zero)
            N_zero = int(len(map)/2)
            m = Minuit(chi2, N_zero = N_zero, error_N_zero = 0.00001, Gamma = 0.5, error_Gamma = 0.1, E_cut = 100000000., error_E_cut = 10., errordef = 1.)
            m.migrad()
            Gamma = m.values['Gamma'] # Spectral index
            N_zero = m.values['N_zero']
            E_cut = m.values['E_cut']
                
            chi2_value = sum((map[binmin:binmax] - N_zero * (Es[binmin:binmax]/E_zero)**(-Gamma) * np.exp(- Es[binmin:binmax]/E_cut))**2 / std_map[binmin:binmax]**2)
            dof = binmax - binmin - 3
            label = r'$\gamma = $%.2f, ' %Gamma + r'$E_{\mathrm{cut}} = $%.1e, ' %E_cut + r'$\frac{\chi^2}{\mathrm{d.o.f.}} =$ %.1f' %(chi2_value / dof)
            pyplot.errorbar(Es[binmin:binmax], [N_zero * (x / E_zero)**(-Gamma) * np.exp(-x/E_cut) for x in Es[binmin:binmax]], label = label, color = colours[colour_index])

        colour_index += 1
        
########################################################################################################################## Plot difference right - left

        
    if plot_diff_leftright:

        map = [0,0]
        std_map = [0,0]
        
        for ell in xrange(nL):
            map[ell]  = np.asarray(diff_profiles[b][ell])
            std_map[ell] = np.asarray(std_profiles[b][ell])

        difference = map[0] - map[1]
        
        total_std = np.sqrt(std_map[0]**2 + std_map[1]**2)
        label_diff = 'difference right - left'
        
        for reading_point in range(len(difference)):
            if difference[reading_point] < 0:
                ms = 4.
                pyplot.errorbar(Es[reading_point], -difference[reading_point], total_std[reading_point], color='lightgrey', marker='>', markersize=ms, markeredgewidth=0.4, linestyle=':', linewidth=0.1)
            else:
                ms = 6.
                pyplot.errorbar(Es[reading_point], difference[reading_point], total_std[reading_point], color='grey', marker='>', markersize=ms, markeredgewidth=0.4, linestyle=':', linewidth=0.1, label=label_diff)
                label_diff = None


                    
########################################################################################################################## Cosmetics, safe plot




    lg = pyplot.legend(loc='upper right', ncol=1, fontsize = 'small')
    lg.get_frame().set_linewidth(0)
    pyplot.grid(True)
    pyplot.xlabel('$E$ [GeV]')
    pyplot.ylabel(r'$ E^2\frac{dN}{dE}\ \left[ \frac{\mathrm{GeV}}{\mathrm{cm^2\ s\ sr}} \right]$')
    pyplot.title(r'SED in latitude stripes, $b \in (%i^\circ$' % (Bc[b] - dB[b]/2) + ', $%i^\circ)$' % (Bc[b] + dB[b]/2))

    name = 'SED_'+ input_data +'_' + str(int(Bc[b]))
    fn = plot_dir + name + fn_ending
    pyplot.xscale('log')
    pyplot.yscale('log')
    pyplot.ylim((1.e-8,4.e-4))
    pyplot.savefig(fn, format = 'pdf')
