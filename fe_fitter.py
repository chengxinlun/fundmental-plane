import math
import os
import numpy as np
import pickle
from scipy.integrate import quad
from scipy.stats import chisquare
import matplotlib.pylab as plt
from astropy.modeling import models, fitting
import warnings
import fe_temp_observed
from base import read_data, get_total_rmid_list, mask_points, check_line, extract_fit_part, save_fig
from position import Location
import time

# Define a special class for raising any exception related during the fit


class SpectraException(Exception):
    pass


# Function to fit quasar with the template
def template_fit(wave, flux, error, rmid):
    img_directory = Location.project_loca + "result/fit_with_temp/fig"
    # Fit continuum
    fig = plt.figure()
    plt.plot(wave, flux)
    [cont_wave, cont_flux, cont_error] = extract_fit_part(wave, flux, error, 4040, 4060)
    [temp_wave, temp_flux, temp_error] = extract_fit_part(wave, flux, error, 5080, 5100)
    cont_wave = np.append(cont_wave, temp_wave)
    cont_flux = np.append(cont_flux, temp_flux)
    cont_error = np.append(cont_error, temp_error)
    cont_fitter = fitting.LevMarLSQFitter()
    cont = models.PowerLaw1D(cont_flux[0], cont_wave[0], - np.log(cont_flux[-1]/cont_flux[0]) / np.log(cont_wave[-1]/cont_wave[0]), fixed = {"x_0": True})
    with warnings.catch_warnings():
        warnings.filterwarnings('error')
        try:
            cont_fit = cont_fitter(cont, cont_wave, cont_flux, weights = cont_error, maxiter = 10000)
        except Exception:
            save_fig(fig, img_directory, str(rmid) + "-cont-failed")
            plt.close()
            raise SpectraException("Continuum fit failed")
    plt.plot(wave, cont_fit(wave))
    save_fig(fig, img_directory, str(rmid) + "-cont-success")
    plt.close()
    # Fit emission lines
    flux = flux - cont_fit(wave)
    fig1 = plt.figure()
    plt.plot(wave, flux)
    hbeta_complex_fit_func = \
            fe_temp_observed.FeII_template_obs(6.2, 2000.0, 2.6, 6.2, 2000.0, 2.6) + \
            models.Gaussian1D(3.6, 4853.30, 7.0, bounds = {"amplitude": [0.0, 50.0], "mean": [4830, 4873], "stddev": [0.0, 23.8]}) + \
            models.Gaussian1D(3.6, 4853.30, 40.0, bounds = {"amplitude": [0.0, 50.0], "mean": [4830, 4873], "stddev": [23.8, 500.0]}) + \
            models.Gaussian1D(2.0, 4346.40, 2.0, bounds = {"amplitude": [0.0, 50.0], "mean": [4323, 4369], "stddev": [0.0, 50.0]}) + \
            models.Gaussian1D(2.0, 4101.73, 2.0, bounds = {"amplitude": [0.0, 50.0], "mean": [4078, 4125], "stddev": [0.0, 50.0]}) + \
            models.Gaussian1D(5.0, 4960.0, 6.0, bounds = {"amplitude": [0.0, 50.0], "mean": [4937, 4983], "stddev": [0.0, 23.8]}) + \
            models.Gaussian1D(20.0, 5008.0, 6.0, bounds = {"amplitude": [0.0, 50.0], "mean": [4985, 5031], "stddev": [0.0, 23.8]})
    fitter = fitting.LevMarLSQFitter()
    with warnings.catch_warnings():
        warnings.filterwarnings('error')
        try:
            start = time.time()
            fit = fitter(hbeta_complex_fit_func, wave, flux, weights = error, maxiter = 3000)
            print("Time taken: ")
            print(time.time() - start)
        except Exception:
            save_fig(fig1, img_directory, str(rmid) + "-failed")
            plt.close()
            raise SpectraException("Fit failed")
    expected = np.array(fit(wave))
    plt.plot(wave, expected)
    save_fig(fig1, img_directory, str(rmid) + "-succeed")
    plt.close()
    rcs = 0
    for i in range(len(flux)):
        rcs = rcs + (flux[i] - expected[i]) ** 2.0
    rcs = rcs / np.abs(len(flux)-17)
    if rcs > 10.0:
        raise SpectraException("Reduced chi-square too large: " + str(rcs))
    return fit.parameters, cont_fit.parameters, rcs


# Function to output fit result
def output_fit(fit_result, rmid, band):
    picklefile = open(Location.project_loca + "result/fit_with_temp/data/" + str(rmid) + "-" + band + ".pkl", "wb")
    pickle.dump(fit_result, picklefile)
    picklefile.close()


# Exception logging process
def exception_logging(rmid, reason):
    log = open(Location.project_loca + "Fe2_fit_error.log", "a")
    log.write(str(rmid) + " " + str(reason) + "\n")
    log.close()


# Individual working process
def main_process(rmid):
    print("Beginning process for " + str(rmid))
    # Read data and preprocessing
    [wave, flux, error] = read_data("coadded", rmid)
    [wave, flux, error] = mask_points(wave, flux,  error)
    [wave, flux, error] = extract_fit_part(wave, flux, error, 4000.0, 5500.0)
    # Begin fitting and handling exception
    try:
        [fit_res, cont_res, rcs] = template_fit(wave, flux, error, rmid)
    except SpectraException as reason:
        exception_logging(rmid, reason)
        print("Failed\n\n")
        return
    output_fit(fit_res, rmid, "Fe2")
    output_fit(cont_res, rmid, "cont")
    print("Finished\n\n")
        
os.chdir(Location.project_loca + "result/")
try:
    os.mkdir("fit_with_temp")
except OSError:
    pass
# rmid_list = get_total_rmid_list()
rmid_list = [131]
os.chdir("fit_with_temp")
try:
    os.mkdir("fig")
except OSError:
    pass
try:
    os.mkdir("data")
except OSError:
    pass
# Start working process
for each_rmid in rmid_list:
    main_process(str(each_rmid))
