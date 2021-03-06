import numpy as np
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt
import pandas as pd
# %%  
def readcheck_input(filename):
    force_imported = pd.read_csv(filename,header = None)
    if force_imported.shape[1] == 3:
        return force_imported.values
    else: raise ValueError('force data must be Nx3 columns [horizontal, horizontal, vertical]')
# %% 
def step_ID(force, threshold, Fs, min_step, max_step):
    '''
    This function reads in FILTERED *running* ground reaction force data and splits steps based on a force threshold.
    Author: Ryan Alcantara || ryan.alcantara@colorado.edu || github.com/alcantarar
    
    Parameters
    -------------
    force :             Nx3 array of FILTERED 3D [horizontal,horizontal,vertical] force data
    threshold :         Threshold in Newtons used to define heel-strike and toe-off. Please be responsible and set < 50N. 
    Fs :                Sampling Frequency of force signal
    min_step :          Min Step Length - Minimum number of frames the step ID algorithm will consider 1 step. Running should be > 0.2*Fs.
    max_step :          Max Step length - Maximum number of frames the step ID algorithm will consider 1 step. Running should be < 0.4*Fs.
    
    Returns
    -------------
    step_begin_all :    Array of frame indexes for beginning of stance phase
    step_end_all :      Array of frame indexes for end of stance phase
    (prints # of suspicious steps and # of step starts/ends too)
    
    Example
    -------------
    >>> step_begin_all, step_end_all = step_ID(force_filtered, 20, 1000, 60, 90) #20N threshold, 1000Hz, 60-90 frame step length OK
    Number of step begin/end: 77 77
    array([101, 213, 323, 435]) #step_begin_all
    array([177, 289, 401, 511]) #step_end_all   
    
    '''
    if min_step < max_step:
        #step Identification Forces over step_threshold register as step (foot on ground).
        compare = (force[:,2] > threshold).astype(int)
    
        events = np.diff(compare)
        step_begin = np.squeeze(np.asarray(np.nonzero(events == 1)).transpose())
        step_end = np.squeeze(np.asarray(np.nonzero(events == -1)).transpose())
    
        #if trial starts with end of step, ignore
        step_end = step_end[step_end > step_begin[0]]
        #trim end of step_begin to match step_end. 
        step_begin = step_begin[0:step_end.shape[0]]
    
        #initialize 
        step_len = np.full(step_begin.shape, np.nan) #step begin and end should be same length...
        step_begin_all = np.full(step_begin.shape, np.nan)
        step_end_all = np.full(step_end.shape, np.nan)
        #calculate step length and compare to min/max step lengths
        step_len = step_end - step_begin
        good_step = np.logical_and(step_len >= min_step, step_len <= max_step) 
        step_begin_all = step_begin[good_step]
        step_end_all = step_end[good_step]
        #ID suspicious steps (too long or short)
        if np.any(step_len < 0.2*Fs):
            print('Out of', step_len.shape[0], 'steps,', sum(step_len < 0.2*Fs), '< 0.20 s. min_step =', min_step/Fs,'s.')
        if np.any(step_len > 0.4*Fs): 
            print('Out of', step_len.shape[0], 'steps,', sum(step_len > 0.4*Fs), '> 0.40 s.')
        #print sizes
        print('Number of step begin/end:',step_end_all.shape[0], step_begin_all.shape[0])
        
        return step_begin_all, step_end_all
      
    else: raise IndexError('Did not separate steps. Min step length > Max step length of 0.4s.')
# %%
def plot_separated_steps(force,begin,end):
    '''
    Plots separated steps on top of each other. Requires an array of beginning/end of stance phase indexes and 3d (dim: Nx3) force data.
    Example: 
    >>> plot_separated_steps(force_filtered, steps[:,0], steps[:,1])
    '''
    colors = plt.cm.viridis(np.linspace(0,1,begin.shape[0]))     

    fig, ax = plt.subplots()
    ax.set_title('All separated steps')
    ax.grid()
    ax.set_xlabel('frames') 
    ax.set_ylabel('force (N)')
    for i in range(end.shape[0]): plt.plot(force[begin[i]:end[i],2], color = colors[i])
    plt.tight_layout()
    plt.pause(.5)
    plt.show(block = False)

# %%
def trim_aerial_phases(force, begin, end):
    '''
    Receives user input to determine how much it needs to trim off the beginning and end of the aerial phase. 
    This is done because filtering can cause artificial negative values where zero values rapidly change to positive values. 
    These changes primarly occur during the beginning/end of stance phase. 
    
    Graph appears with vertical black lines at the beginning/end of the a aerial phase. Function is
    waiting for two mouse clicks on plot where you'd like to trim the aerial phase. Click within the two black vertical lines!
    
    Returns:
    -------------
    trim :        Amount of frames to trim off the beginning and end of each aerial phase. Is average of userinputs.
    
    '''
    #plot a first 2 steps and get user input for how much to trim off beginning/end of aerial phase
    trim_fig, ax = plt.subplots()
    ax.plot(force[begin[0]:end[1],2],
            color = 'tab:blue')
    start_a = force[begin[0]:end[1],2] == force[end[0],2]
    end_a = force[begin[0]:end[1],2] == force[begin[1],2]
    ax.axvline(start_a.nonzero(),color = 'k')
    ax.axvline(end_a.nonzero(),color = 'k')
    ax.set_title('select how much to trim off beginning/end \n of aerial phase (between black lines)')
    ax.set_xlabel('frames')
    ax.set_ylabel('force (N)')
    plt.tight_layout()

    #user input from mouse click
    bad_points = 1
    while bad_points:
        points = np.asarray(plt.ginput(2, timeout = 0),dtype = int)
        
        if sum(points[:,0] < start_a.nonzero()[0][0]) > 0 or sum(points[:,0] > end_a.nonzero()[0][0]) > 0: 
            #points outside of range
            print("Can't trim negative amount. Select 2 points between start/end of aerial phase")
        elif points[1,0] < points[0,0]: 
            #points in wrong order
            print("First select amount to trim off the start, then select the amount to trim off the end of aerial phase")
        else:
            trim = (np.round((points[0,0]-start_a.nonzero()[0][0] + end_a.nonzero()[0][0]-points[1,0])/2)).astype(int)
            print('trimming ',trim,' frames from the start/end of aerial phase')
            bad_points = 0
            plt.close(trim_fig)
    
    #can't trim more than step length, but assume trim is good and step length is bad.        
    aerial_begin = end[:-1]
    aerial_end = begin[1:]
    aerial_len = aerial_end-aerial_begin 
    if np.any(aerial_len < trim*2): raise IndexError('Trim amount is greater than aerial phase length. If trim selection was reasonable, adjust threshold or min_step_len.')
    
    return trim
  
# %%
def plot_aerial_phases(force, aerial_means, begin, end, trim, colormap = plt.cm.viridis):
    '''
    Plotting function for detrend_force. Plots 1) All the untrimmed aerial phases, 2) All the trimmed aerial phases, 
    and 3) the means of the trimmed aerial phases. Visualizes the means used to account for drift in detrend_force function.
    
    '''
    if aerial_means.shape[0] == begin.shape[0] == end.shape[0]:
        colors = colormap(np.linspace(0,1,begin.shape[0]))     
        plt.fig, (untrimp, trimp, meanp) = plt.subplots(3,1,sharex = False, figsize = (15,7))
        
        #plot of untrimmed aerial phases
        untrimp.set_title('untrimmed aerial phases')
        untrimp.set_ylabel('force (N)')
        untrimp.grid()
        for i in range(begin.shape[0]):
            untrimp.plot(force[begin[i]:end[i],2],
                         color = colors[i])  
        #plot of trimmed aerial phases    
        trimp.set_title('trimmed aerial phases')
        trimp.set_ylabel('force (N)')
        trimp.grid()
        for i in range(begin.shape[0]):
            trimp.plot(force[begin[i]+trim:end[i]-trim,2],
                       color = colors[i])
        #plot all the means of trimmed aerial phases
        meanp.set_title('mean of trimmed aerial phases')
        meanp.set_xlabel('steps')
        meanp.set_ylabel('force (N)')
        meanp.grid()
        for i in range(begin.shape[0]):
            meanp.plot(i,aerial_means[i,2],
                       marker = 'o',
                       color = colors[i])   
        plt.show(block = False)
# %%
def detrend_force(filename,Fs,Fc,min_step,step_threshold = 100,plots = False):
    '''
    This function reads in a text file of 3D *running* ground reaction force data and removes drift in a stepwise manner.
    Author: Ryan Alcantara || ryan.alcantara@colorado.edu || github.com/alcantarar
    
    Parameters
    -------------
    filename :          filename of Nx3 array of 3D [horizontal,horizontal,vertical] force data to import via pd.read_csv.
    Fs :                Sampling frequency of force data.
    Fc :                Cut off frequency for 4th order zero-lag butterworth filter.
    min_step :          Minimum number of frames the step ID algorithm will consider 1 step. Default max_step is 0.4*Fs.
    step_threshold :    (optional) threshold in Newtons used to define heel-strike and toe-off. Default is 100N because
                        it is better to be aggressive for detrending. Can re-run Step_ID function with a reasonable 
                        step_threshold once signal is detrended.
    plots :             (optional) Logical input to receive graphs depicting detrend process.
    
    Returns
    -------------
    force_fd :          Nx3 array of filtered, detrended 3D force data 
    aerial_means :      Mean of force during aerial phase for original signal
    aerial_means_d :    Mean of force during aerial phase for detrended signal
    
    Raises
    -------------
    ValueError
        if imported file is not Nx3 dimensions. Requires 3D force data: [horizontal, horizontal, vertical].
    
    IndexError
        if aerial phase is exceptionally short. Happens when step identification is poor. Check plots and increase step_threshold or min_step 
        
    Examples
    -------------
    >>> fname = '/Users/alcantarar/data/drifting_forces.csv'    
    >>> force_fd, aerial_means, aerial_means_d = detrend_force(fname, Fs=300, Fc=60, min_step=60) #step_threshold = 100N, no plots
    #OR
    >>> force_fd,_,_ = detrend_force('drifting_forces.csv',300,60,60,100,True) #suppress aerial means outputs 
    
    '''
    force = readcheck_input(filename)
    #filter 4th order zero lag butterworth
    fn = (Fs/2)
    b,a = butter(2,Fc/fn)
    force_f = filtfilt(b,a,force,axis = 0) #filtfilt doubles order (2nd*2 = 4th order effect)
        
    # %% split steps and create aerial phases
    max_step = 0.4*Fs 
    step_begin_all, step_end_all= step_ID(force_f,step_threshold, Fs, min_step, max_step)

    #create aerial phases (foot not on ground) and trim artefacts from filtering
    aerial_begin_all = step_end_all[:-1]
    aerial_end_all = step_begin_all[1:]
    print('Number of aerial begin/end:',aerial_begin_all.shape[0],aerial_end_all.shape[0]) #matching number of step beginnings/ends
    
    if plots:
        plot_separated_steps(force_f, step_begin_all, step_end_all)
        plt.tight_layout()

    # %% trim filtering artefact and calculate mean of each aerial phase
    trim = trim_aerial_phases(force_f, step_begin_all, step_end_all)
    
    #calculate mean force during aerial phase (foot not on ground, should be zero)
    aerial_means = np.full([aerial_begin_all.shape[0],3], np.nan)
    for i in range(aerial_begin_all.shape[0]):
        aerial_means[i,0] = np.mean(force_f[aerial_begin_all[i]+trim:aerial_end_all[i]-trim,0])
        aerial_means[i,1] = np.mean(force_f[aerial_begin_all[i]+trim:aerial_end_all[i]-trim,1])
        aerial_means[i,2] = np.mean(force_f[aerial_begin_all[i]+trim:aerial_end_all[i]-trim,2])
    
    #plot aerial phases
    if plots:
        plot_aerial_phases(force_f, aerial_means, aerial_begin_all, aerial_end_all, trim)
        plt.tight_layout()

    # %% Detrend signal    
    force_fd = np.zeros(force_f.shape)
    diff_vals = []

    for i in range(aerial_means.shape[0]-1):
        diff_temp = (aerial_means[i,2]+aerial_means[i+1,2])/2 #mean between two subsequent aerial phases
        diff_vals.append(diff_temp)
        force_fd[step_begin_all[i]:step_begin_all[i+1],:] = force_f[step_begin_all[i]:step_begin_all[i+1],:] - diff_temp
        
    if plots != False:            
        #plot raw vs detrended
        plt.detrendp, (sigcomp, meancomp) = plt.subplots(2,1,sharex = False, figsize =  (15,7))
        sigcomp.plot(np.linspace(0,force_fd.shape[0]/Fs,force_fd.shape[0]),
                 force_f[:,2],
                 color = 'tab:blue',
                 alpha = 0.7) #converted to sec
        sigcomp.plot(np.linspace(0,force_fd.shape[0]/Fs,force_fd.shape[0]),
                 force_fd[:,2],
                 color = 'tab:red',
                 alpha = 0.7) #converted to sec
        sigcomp.grid()
        sigcomp.legend(['original signal','detrended signal'], loc = 1)
        sigcomp.set_xlabel('Seconds')
        sigcomp.set_ylabel('force (N)')
    
    #calculate mean aerial for detrend data
    aerial_means_d = np.zeros(aerial_means.shape[0])
    #gb - could use list comp (?) here to speed it up
    for i in range(aerial_begin_all.shape[0]):
        aerial_means_d[i] = np.mean(force_fd[aerial_begin_all[i]+trim:aerial_end_all[i]-trim,2]) #just vertical force
    aerial_means_d = aerial_means_d[aerial_means_d !=0.0]

    if plots:
        #plot detrend vs old mean aerial
        meancomp.set_title('mean of aerial phases')
        meancomp.set_xlabel('steps')
        meancomp.set_ylabel('force (N)')
        meancomp.grid()
        #np.ylim([-20,20])
        for i in range(aerial_means.shape[0]-1):
            meancomp.plot(i,aerial_means[i,2],
                     marker = '.',
                     color = 'tab:blue',
                     label = 'original signal')
            meancomp.plot(i,aerial_means_d[i],
                     marker = '.', 
                     color = 'tab:red', 
                     label = 'detrended signal')
            meancomp.legend(['original signal','detrended signal'], loc = 1) #don't want it in loop, but it needs it?
        plt.tight_layout()

    plt.show(block = False)
    
    return force_fd, aerial_means, aerial_means_d 
    
# %% EXAMPLE:
force_fd, aerial_means, aerial_means_d = detrend_force('cat6.csv',Fs = 1000, Fc = 30,min_step = 40, step_threshold = 200, plots = True)

