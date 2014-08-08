from scipy.signal import butter, lfilter
from copy import copy, deepcopy
from datetime import datetime, timedelta
from miic.core.miic_utils import convert_time, convert_time_to_string
import numpy as np


def corr_mat_filter(corr_mat, freqs, order = 3):
    """ Filter a correlation matrix.

    Filters the correlation matrix corr_mat in the frequency band specified in
    freqs using a zero phase filter of twice the order given in order.

    :type corr_mat: dictionary of the type correlation matrix
    :param corr_mat: correlation matrix to be plotted
    :type freqs: array-like of length 2
    :param freqs: lower and upper limits of the pass band in Hertz
    :type order: int
    :param order: half the order of the Butterworth filter

    :rtype tdat: dictionary of the type correlation matrix
    :return: **fdat**: filtered correlation matrix
    """
    from scipy.signal import butter, lfilter
    # check input
    if not isinstance(corr_mat,dict):
        print "corr_mat needs to be correlation matrix dictionary."""
        return 0
    if len(freqs) != 2:
        print "freqs needs to be a two element array with the lower and upper limits of the filter band in Hz."
        return 0

    (b,a) = butter(order, np.array(freqs) / corr_mat['stats']['sampling_rate'], btype='band')
    fdat = copy(corr_mat)
    fdat['corr_data'] = lfilter(b, a, fdat['corr_data'], axis=1)
    fdat['corr_data'] = lfilter(b, a, fdat['corr_data'][:, -1::-1], axis=1)[:, -1::-1]

    return fdat


def corr_mat_trim(corr_mat, starttime, endtime):
    """ Trim the correlation matrix to a given period.

    Trim the correlation matrix `corr_mat` to the period from `starttime` to
    `endtime` given in seconds from the zero position, so both can be
    positive and negative. If `starttime` and `endtime` are datetime.datetime
    objects they are taken as absolute start and endtime.

    :type corr_mat: dictionary of the type correlation matrix
    :param corr_mat: correlation matrix to be trimmed
    :type starttime: float or datetime.datetime object
    :param starttime: start time in seconds with respect to the zero position
    :type endtime: float or datetime.datetime object
    :param order: end time in seconds with respect to the zero position

    :rtype tdat: dictionary of the type correlation matrix
    :return: **tdat**: trimmed correlation matrix
    """
    
    # check input

    # copy the dictionary
    tdat = deepcopy(corr_mat)
    print tdat['corr_data'].shape

    # definition of the source time of a Green's function (ie. zero correlation
    # time)
    zerotime = datetime(1971, 1, 1, 0, 0, 0)
    
    if isinstance(starttime,datetime):
        start = starttime - convert_time([corr_mat['stats']['starttime']])[0]
        end = endtime - convert_time([corr_mat['stats']['starttime']])[0]
    else:
        # time from zerotime to start and end
        stime = timedelta(float(starttime) / 86400)
        etime = timedelta(float(endtime) / 86400)
        # first and last sample
        start = zerotime - convert_time([corr_mat['stats']['starttime']])[0] + stime
        end = zerotime - convert_time([corr_mat['stats']['starttime']])[0] + etime
    
    #print start
    start = int(np.floor(start.total_seconds() * corr_mat['stats']['sampling_rate']))
    #print end
    end = int(np.ceil(end.total_seconds() * corr_mat['stats']['sampling_rate']))
    
    # check range
    if start<0:
        print 'Error: starttime before beginning of trace. Data not changed'
        return tdat
    if end>= corr_mat['stats']['npts']:
        print 'Error: endtime after end of trace. Data not changed'
        return tdat
    
    print start, end
    # select requested part from matrix
    tdat['corr_data'] = tdat['corr_data'][:, start: end+1]   # +1 is to include the last sample
    
    # set starttime, endtime and npts of the new stats
    tdat['stats']['starttime'] = convert_time_to_string([convert_time([corr_mat['stats']['starttime']])[0] + 
                timedelta(seconds = float(start) * 1./corr_mat['stats']['sampling_rate'])])[0]
    tdat['stats']['endtime'] = convert_time_to_string([convert_time([corr_mat['stats']['starttime']])[0] + 
                timedelta(seconds = float(end) * 1./corr_mat['stats']['sampling_rate'])])[0]
    tdat['stats']['npts'] = end - start + 1

    return tdat


def corr_mat_merge(corr_mat_list,network=None,station=None,location=None,channel=None):
    """ Merge correlation matrices.
    
    If different correlation matrices are created for the same station
    combination they can be merged with this function. NO CHECK IS PERFORMED
    FOR CONSISTENCY OF METADATA. Please check yourself that it makes sense to
    merge the data. Timing information is handled. If `network`, `station`,
    `location` or `channel` is provided the combined seed ID of the merged
    correlation matrix is set to these values. Otherwise the ID of the first
    correlation matrix in the list is used for the merged matrix.
    
    :type corr_mat_list: list of dictionarys of the type correlation matrix
    :param corr_mat: list of correlation matrices to be merged


    :rtype mdat: dictionary of the type correlation matrix
    :return: **mdat**: merged correlation matrix
    """
    
    # check input
    
    zerotime = datetime(1971,1,1)
    # estimate required size for the merged correlation matrix
    ntrc = 0
    starttime = convert_time([corr_mat_list[0]['stats']['starttime']])[0]
    sampling_rate = corr_mat_list[0]['stats']['sampling_rate']
    endtime = convert_time([corr_mat_list[0]['stats']['starttime']])[0]+ \
                timedelta((float(corr_mat_list[0]['stats']['npts'])-1.)*1./sampling_rate/86400.)
    lentrc = np.Inf
    times = []
    for corr_mat in corr_mat_list:
        if corr_mat['stats']['sampling_rate'] != sampling_rate:
            continue
        size = corr_mat['corr_data'].shape
        ntrc += size[0]
        this_starttime = convert_time([corr_mat['stats']['starttime']])[0]
        print corr_mat['stats']['starttime'], type(this_starttime)
        this_endtime = this_starttime + timedelta(seconds = (float(corr_mat['stats']['npts'])-1.)*1./sampling_rate)
        starttime = max([starttime,this_starttime])
        endtime = min([endtime, this_endtime])
    
    
    print starttime, endtime
    # create merged dictionary  
    mdat = deepcopy(corr_mat_list[0])
    # trim the first matrix
    mdat = corr_mat_trim(mdat,starttime,endtime)
    for corr_mat in corr_mat_list[1:]:
        if corr_mat['stats']['sampling_rate'] != sampling_rate:
            continue
        tdat = corr_mat_trim(corr_mat,starttime,endtime)
        mdat['corr_data'] = np.concatenate((mdat['corr_data'], tdat['corr_data']),axis=0)
        mdat['time'] = np.concatenate((mdat['time'],corr_mat['time']),axis=0)
    
    # set the combined seed ID
    if network:
        mdat['stats']['network'] = network
    if station:
        mdat['stats']['station'] = station
    if location:
        mdat['stats']['location'] = location
    if channel:
        mdat['stats']['channel'] = channel
    
    
    return mdat



def corr_mat_resample(corr_mat, start_times, end_times=[]):
    """ Function to create correlation matrices with constant sampling

    When created with recombine_corr_data the correlation matrix contains all
    available correlation streams but homogeneous sampling is not guaranteed
    as correaltion functions may be missing due to data gaps. This function
    restructures the correlation matrix by inserting or averaging correlation
    functions to provide temporally homogeneous sampling. Inserted correlation
    functions consist of 'nan' if gaps are present and averaging is done if
    more than one correlation function falls in a bin between start_times[i]
    and end_times[i]. If end_time is an empty list (default) end_times[i] is
    set to start_times[i] + (start_times[1] - start_times[0])

    :type corr_mat: dictionary
    :param corr_mat: correlation matrix dictionary as produced by
        :class:`~miic.core.macro.recombine_corr_data`
    :type start_times: list of class:`~datetime.datetime` objects or equvalent
        strings (see :class:`~miic.core.miic_utils.convert_time`)
    :param start_times: list of starting times for the bins of the new
        sampling
    :type end_times: list of class:`~datetime.datetime` objects or equvalent
        strings (see :class:`~miic.core.miic_utils.convert_time`)
    :param end_times: list of starting times for the bins of the new sampling

    :rtype: dictionary
    :return: **corr_mat**: is the same dictionary as the input but with
        adopted corr_mat['corr_data'] and corr_mat['time'] keys.
    """

    # check input
    req_keys = ['corr_data', 'time']
    if not isinstance(corr_mat, dict):
        print 'corr_mat must be a dictionary of type correlation_matrix'
        return None
    for rk in req_keys:
        if not rk in corr_mat.keys():
            print 'key %s is missing in dictionary' % rk
            return None
    if len(end_times) > 0 and (len(end_times) != len(start_times)):
        print 'end_times should be empty or of the same length as start_times'
        return None

    # old sampling times
    otime = convert_time(corr_mat['time'])

    # new sampling times
    stime = convert_time(start_times)
    if len(end_times) > 0:
        etime = convert_time(end_times)
    else:
        if len(start_times) == 1:
            # there is only one start_time given and no end_time => average all
            etime = [otime[-1]]
            #print etime
        else:
            etime = stime + (stime[1] - stime[0])

    # new corr_data matrix
    nmat = np.empty([len(stime), corr_mat['corr_data'].shape[1]])
    nmat.fill(np.nan)

    for ii in range(len(stime)):
        # index of measurements between start_time[ii] and end_time[ii]
        ind = np.nonzero((otime >= stime[ii]) * (otime < etime[ii]))  # ind is
                                                #  a list(tuple) for dimensions
        if len(ind[0]) == 1:
            # one measurement found
            nmat[ii, :] = corr_mat['corr_data'][ind[0], :]
        elif len(ind[0]) > 1:
            # more than one measurement in range
            nmat[ii, :] = np.mean(corr_mat['corr_data'][ind[0], :], 0)
        #print 'ind[0] :', ind[0]

    # assign new data
    corr_mat['corr_data'] = nmat
    corr_mat['time'] = convert_time_to_string(stime)

    return corr_mat


def corr_mat_reverse(corr_mat):
    """ Reverse the data in a correlation matrix.

    If a correlation matrix was calculated for a pair of stations sta1-sta2
    this function reverses the causal and acausal parts of the correlation
    matrix as if the correlations were calculated for the pair sta2-sta1.

    :type corr_mat: dictionary
    :param corr_mat: correlation matrix dictionary as produced by
        :class:`~miic.core.macro.recombine_corr_data`

    :rtype: dictionary
    :return: **corr_mat**: is the same dictionary as the input but with
        reversed order of the station pair.
    """

    # check input
    zerotime = datetime(1971,1,1)

    # reverse the stats_tr1 and stats_tr2
    stats_tr1 = corr_mat['stats_tr1']
    corr_mat['stats_tr1'] = corr_mat['stats_tr2']
    corr_mat['stats_tr2'] = stats_tr1

    # reverse the locations in the stats
    stla = corr_mat['stats']['stla']
    stlo = corr_mat['stats']['stlo']
    stel = corr_mat['stats']['stel']
    corr_mat['stats']['stla'] = corr_mat['stats']['evla']
    corr_mat['stats']['stlo'] = corr_mat['stats']['evlo']
    corr_mat['stats']['stel'] = corr_mat['stats']['evel']
    corr_mat['stats']['evla'] = stla
    corr_mat['stats']['evlo'] = stlo
    corr_mat['stats']['evel'] = stel
    # reverse the combined stats
    

    # reverse the matrix
    corr_mat['corr_data'] = corr_mat['corr_data'][:,-1::-1]

    # adopt the starttime and endtime
    trace_length = timedelta(seconds=float(corr_mat['stats']['npts'])/corr_mat['stats']['sampling_rate'])
    endtime = convert_time([corr_mat['stats']['starttime']])[0] + trace_length
    print endtime
    starttime = zerotime - (endtime-zerotime)
    print starttime
    corr_mat['stats']['starttime'] = convert_time_to_string([starttime])[0]
    corr_mat['stats']['endtime'] = convert_time_to_string([starttime + trace_length])[0]
    
    return corr_mat


def corr_mat_time_select(corr_mat, starttime=None, endtime=None):
    """ Select time period from a correlation matrix.

    Select correlation  traces from a correlation matrix that fall into the
    time period `starttime`<= selected times <= `endtime` and return them in
    a correlation matrix.

    :type corr_mat: dictionary
    :param corr_mat: correlation matrix dictionary as produced by
        :class:`~miic.core.macro.recombine_corr_data`
    :type starttime: datetime.datetime object or time string
    :param starttime: beginning of the selected time period
    :type endtime: datetime.datetime object or time string
    :param endtime: end of the selected time period

    :rtype: dictionary
    :return: **corr_mat**: correlation matrix dictionary restricted to the
        selected time period.
    """

    # check input
    
    smat = deepcopy(corr_mat)

    # convert time vector
    time = convert_time(corr_mat['time'])

    # convert starttime and endtime input.
    # if they are None take the first or last values of the time vector
    if starttime == None:
        starttime = time[0]
    else:
        if not isinstance(starttime,datetime):
            starttime = convert_time([starttime])[0]
    if endtime == None:
        endtime = time[-1]
    else:
        if not isinstance(endtime,datetime):
            endtime = convert_time([endtime])[0]

    # select period
    ind = np.nonzero((time >= starttime) * (time < endtime))[0]  # ind is
                                                #  a list(tuple) for dimensions
    
    # trim the matrix
    smat['corr_data'] = corr_mat['corr_data'][ind,:]

    # adopt time vector
    smat['time'] = corr_mat['time'][ind]

    return smat






