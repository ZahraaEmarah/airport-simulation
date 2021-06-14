import simpy
import random
from matplotlib import pyplot as plt

RANDOM_SEED = 6930352520
OBS_TIME = 500  # Simulation time in minutes
allow_no_baggage = True
allow_pre_check = True

id_check_booth = object
preparation_booth = object
passenger_scan_machine = object
baggage_scan_machine = object
additional_scanner = object

# for plotting
list_TW = []
list_TS = []
list_TRES = []

number_of_passengers = 0
completed_jobs = 0
no_bag_passengers = 0
no_bag_passengers_completed = 0
pre_check_passengers = 0
pre_check_passengers_completed = 0


class b_colors:
    OKGREEN = '\033[92m'
    OKBLUE = '\033[94m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'
    CSELECTED = '\33[7m'
    CVIOLETBG = '\33[45m'
    pink = '\033[95m'


class Machines(object):
    def __init__(self, env, number_of_servers, service_time):
        self.env = env
        self.machine = simpy.Resource(env, number_of_servers)
        self.service_time = service_time

    def serve(self):
        yield self.env.timeout(self.service_time + random.expovariate(0.5))  # exponential service time

    def pre_check(self):
        yield self.env.timeout((self.service_time / 2) + random.expovariate(0.5))


def process_a(env, name, id_machine):
    global allow_no_baggage
    arrival_time = env.now
    waiting_time = env.now

    print('Zone A: %s arrives at the airport at %.2f.' % (name, arrival_time))

    # stand in the ID check queue
    with id_machine.machine.request() as request:
        yield request  # wait for their turn

        waiting_time = env.now - waiting_time  # calculate how much they waited
        service_time = env.now  # start calculating the service time

        print('Zone A: %s started ID checking at %.2f.' % (name, env.now))
        yield env.process(id_machine.serve())  # check ID here
        service_time = env.now - service_time  # calculate service time

        print(
            'Zone A: %s Finished ID checking at %.2f. \t || Process A SERVICE TIME: %d / WAITING TIME: %d' % (
                name, env.now, service_time, waiting_time))

        no_baggage = random.randint(0, 10)  # does this passenger have a bag or not ?
        # if the passenger doesnt have a bag go straight to B2(Passenger scanner)
        if allow_no_baggage and no_baggage >= 8:  # 20% No baggage

            global no_bag_passengers
            no_bag_passengers += 1

            print(f'{b_colors.CSELECTED}Zone A: %s has no baggage Proceeding to B2{b_colors.ENDC} ' % name)
            b2_tw, b2_ts = yield env.process(
                process_b2(env, name, passenger_scan_machine))
            env.process(
                exit_airport(name, arrival_time, waiting_time + b2_tw, service_time + b2_ts, True, False))

        else:
            b1_tw, b1_ts, is_pre_check = yield env.process(process_b1(env, name, preparation_booth))
            print("b1 returned ", is_pre_check, name)
            env.process(exit_airport(name, arrival_time, waiting_time + b1_tw, service_time + b1_ts, False,
                                     is_pre_check))


def process_b1(env, name, belongings_box):
    print('Zone B1: %s arrives at the Preparation booth at %.2f.' % (name, env.now))
    tw = env.now

    # stand in line
    with belongings_box.machine.request() as request:
        yield request
        tw = env.now - tw
        print('Zone B1: %s start preparing belongings %.2f.' % (name, env.now))

        # if pre-check passenger their service time is half the usual service time
        if allow_pre_check and random.randint(0, 10) >= 5:

            print(f'{b_colors.pink}Passenger %s is a member of the Pre-Check program{b_colors.ENDC}' % name)
            ts = env.now
            yield env.process(belongings_box.pre_check())  # prepare belongings
            ts = env.now - ts  # calculate service time

            global pre_check_passengers
            pre_check_passengers += 1
            pre_check = True

        else:
            ts = env.now
            yield env.process(belongings_box.serve())  # prepare belongings
            ts = env.now - ts  # calculate service time
            pre_check = False

        print(
            'Zone B1: %s Finished preparing belongings %.2f.\t || Process B1 SERVICE TIME: %d / WAITING TIME: %d' % (
                name, env.now, ts, tw))

        # go to passenger scanner
        b2_tw, b2_ts = yield env.process(process_b2(env, name, passenger_scan_machine))
        # go to baggage scanner
        b3_tw, b3_ts = yield env.process(process_b3(env, name, baggage_scan_machine))

        return (tw + b2_tw + b3_tw), (ts + b2_ts + b3_ts), pre_check


def process_b2(env, name, passenger_scanner):
    print('Zone B2: %s arrives at the Passenger scanner at %.2f.' % (name, env.now))
    tw = env.now  # initialize waiting time

    # stand in line
    with passenger_scanner.machine.request() as request:
        yield request

        tw = env.now - tw  # calculate how much they waited
        ts = env.now
        # start scan procedure
        print('Zone B2: %s starts Passenger scanning %.2f.' % (name, env.now))
        yield env.process(passenger_scanner.serve())
        ts = env.now - ts  # calculate service time
        print('Zone B2: %s Finished Passenger scanning %.2f.\t || Process B2 SERVICE TIME: %d / WAITING TIME: %d' % (
            name, env.now, ts, tw))
    return tw, ts


def process_b3(env, name, baggage_scanner):
    print('Zone B3: %s Baggage arrives at the Baggage scanner at %.2f.' % (name, env.now))
    tw = env.now

    # baggage waits in queue
    with baggage_scanner.machine.request() as request:
        yield request

        tw = env.now - tw
        ts = env.now

        # start scanning procedure
        print('Zone B3: %s starts Baggage scanning %.2f.' % (name, env.now))
        yield env.process(baggage_scanner.serve())
        ts = env.now - ts

        print('Zone B3: %s Finished Baggage scanning %.2f.\t || Process B3 SERVICE TIME: %d / WAITING TIME: %d' % (
            name, env.now, ts, tw))
        return tw, ts


def process_d(env, name, fail_re_scan):
    print('Zone D: %s arrives at the Additional scanner at %.2f.' % (name, env.now))
    tw = env.now
    # stands in line
    with fail_re_scan.machine.request() as request:
        yield request

        tw = env.now - tw
        ts = env.now
        print('Zone D: %s starts Additional scanning %.2f.' % (name, env.now))
        yield env.process(fail_re_scan.serve())
        ts = env.now - ts

        print('Zone D: %s Finished Additional scanning %.2f.\t || Process D SERVICE TIME: %d / WAITING TIME: %d' % (
            name, env.now, ts, tw))
    return tw, ts


def exit_airport(name, arrival_time, total_tw, total_ts, is_no_baggage, is_precheck):

    fail_flag = random.randint(0, 10)
    if fail_flag >= 7:
        print(f'{b_colors.FAIL}%s Failure{b_colors.ENDC}' % name)
        d_tw, d_ts = yield env.process(process_d(env, name, additional_scanner))
        total_tw = total_tw + d_tw
        total_ts = total_ts + d_ts
        print(
            f'{b_colors.OKBLUE}Zone D: %s Left the airport at %.2f\t || TOTAL_TW: %d / TOTAL TS: %d / RESPONSE TIME: %d{b_colors.ENDC}' % (
                name, env.now, total_tw, total_ts, (env.now - arrival_time)))
    else:
        print(
            f'{b_colors.OKBLUE}Zone C: %s Left the airport at %.2f\t || TOTAL_TW: %d / TOTAL TS: %d / RESPONSE TIME: %d{b_colors.ENDC}' % (
                name, env.now, total_tw, total_ts, (env.now - arrival_time)))

    list_TS.append(total_ts)
    list_TW.append(total_tw)
    list_TRES.append(env.now - arrival_time)

    global completed_jobs
    completed_jobs = completed_jobs + 1

    if is_no_baggage:
        global no_bag_passengers_completed
        no_bag_passengers_completed += 1

    if is_precheck:
        global pre_check_passengers_completed
        pre_check_passengers_completed += 1


def setup(env):
    # Assumptions
    num_servers = 3

    a_time = 2
    b1_time = 6
    b2_time = 4
    b3_time = 4
    d_time = 10

    # Create the airport machines
    global id_check_booth
    id_check_booth = Machines(env, num_servers, a_time)
    global preparation_booth
    preparation_booth = Machines(env, num_servers, b1_time)
    global passenger_scan_machine
    passenger_scan_machine = Machines(env, 1, b2_time)
    global baggage_scan_machine
    baggage_scan_machine = Machines(env, 1, b3_time)
    global additional_scanner
    additional_scanner = Machines(env, 1, d_time)

    while True:
        global number_of_passengers
        yield env.timeout(random.expovariate(0.1))  # Poisson arrivals
        number_of_passengers += 1
        env.process(process_a(env, 'Passenger %d' % number_of_passengers, id_check_booth))


def average(lst):
    if len(lst) >= 1:
        return sum(lst) / len(lst)


# Setup and start the simulation
print('Airport Simulation \n')
random.seed(RANDOM_SEED)

env = simpy.Environment()
env.process(setup(env))
env.run(until=OBS_TIME)
print(
    f'{b_colors.WARNING}\nPerformance metrics: Avg TW: %.2f, Avg TS: %.2f, Avg response time: %.2f\nCompleted %d jobs, %d with no bags and %d precheck' % (
        average(list_TW), average(list_TS), average(list_TRES), completed_jobs, no_bag_passengers_completed,
        pre_check_passengers_completed))
print('Total Number of Passengers = %d' % number_of_passengers)
print('Total Passengers with no baggage = %d' % no_bag_passengers)
print('Total Pre check program passengers %d' % pre_check_passengers)

plt.xlabel('Performance metrics')
plt.plot(list_TW, label='Waiting Time')
plt.plot(list_TS, label='Service Time')
plt.plot(list_TRES, label='Response Time')
plt.legend()
plt.show()
