import simpy
import random
from matplotlib import pyplot as plt

RANDOM_SEED = 12345678966
OBS_TIME = 300  # Simulation time in minutes
allow_no_baggage = False
allow_pre_check = False

id_check_booth = object
preparation_booth = object
passenger_scan_machine = object
baggage_scan_machine = object
additional_scanner = object

list_TW = []
list_TS = []
list_TRES = []
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


class Machines(object):
    def __init__(self, env, number_of_servers, service_time):
        self.env = env
        self.machine = simpy.Resource(env, number_of_servers)
        self.service_time = service_time

    def serve(self):
        yield self.env.timeout(self.service_time + random.expovariate(0.5))  # exponential service time

    def pre_check(self):
        yield self.env.timeout((self.service_time/2) + random.expovariate(0.5))


def process_a(env, name, id_machine):
    global allow_no_baggage
    arrival_time = env.now
    print('Zone A: %s arrives at the airport at %.2f.' % (name, arrival_time))
    waiting_time = env.now
    no_baggage = random.randint(0, 10)
    with id_machine.machine.request() as request:
        yield request
        waiting_time = env.now - waiting_time
        service_time = env.now
        print('Zone A: %s enters the checkpoint at %.2f.' % (name, env.now))
        yield env.process(id_machine.serve())
        service_time = env.now - service_time
        print(
            'Zone A: %s Finished ID checking at %.2f. \t || Process A SERVICE TIME: %d / WAITING TIME: %d' % (
                name, env.now, service_time, waiting_time))
        if allow_no_baggage and no_baggage > 5:
            global no_bag_passengers
            no_bag_passengers += 1
            print(f'{b_colors.FAIL}Zone A: %s has no baggage Proceeding to B2{b_colors.ENDC} ' % name)
            env.process(process_b2(env, name, passenger_scan_machine, arrival_time, waiting_time, service_time, True, False))
        else:
            env.process(process_b1(env, name, preparation_booth, arrival_time, waiting_time, service_time))


def process_b1(env, name, belongings_box, arrival_time, waiting_time, service_time):
    print('Zone B1: %s arrives at the Preparation booth at %.2f.' % (name, env.now))
    tw = env.now
    print(belongings_box.service_time)
    with belongings_box.machine.request() as request:
        yield request
        tw = env.now - tw
        ts = env.now
        print('Zone B1: %s start preparing belongings %.2f.' % (name, env.now))
        # is pre-check passenger or not
        if allow_pre_check and random.randint(0, 10) > 5:
            yield env.process(belongings_box.pre_check())
            global pre_check_passengers
            pre_check_passengers += 1
            precheck = True
        else:
            yield env.process(belongings_box.serve())
            precheck = False

        ts = env.now - ts
        print(
            'Zone B1: %s Finished preparing belongings %.2f.\t || Process B1 SERVICE TIME: %d / WAITING TIME: %d' % (
                name, env.now, ts, tw))
        env.process(process_b2(env, name, passenger_scan_machine, arrival_time, tw + waiting_time, ts + service_time, False, precheck))
        env.process(process_b3(env, name, baggage_scan_machine, arrival_time, tw + waiting_time, ts + service_time))


def process_b2(env, name, passenger_scanner, arrival_time, waiting_time, service_time, nobag, precheck):
    print('Zone B2: %s arrives at the Passenger scanner at %.2f.' % (name, env.now))
    tw = env.now
    with passenger_scanner.machine.request() as request:
        yield request
        tw = env.now - tw
        ts = env.now
        print('Zone B2: %s starts Passenger scanning %.2f.' % (name, env.now))
        yield env.process(passenger_scanner.serve())
        ts = env.now - ts
        print('Zone B2: %s Finished Passenger scanning %.2f.\t || Process B2 SERVICE TIME: %d / WAITING TIME: %d' % (
            name, env.now, ts, tw))
        fail_flag = random.randint(0, 10)
        if fail_flag > 5:
            print(f'{b_colors.FAIL}Zone B3: %s Failure{b_colors.ENDC}' % name)
            env.process(process_d(env, name, additional_scanner, arrival_time, tw + waiting_time, ts + service_time, nobag, precheck))
        else:
            print(
                f'{b_colors.OKBLUE}Zone C: %s Left the airport \t || TOTAL_TW: %d / TOTAL TS: %d / RESPONSE TIME: %d{b_colors.ENDC}' % (
                    name, (tw + waiting_time), (ts + service_time), (env.now - arrival_time)))
            list_TS.append(ts + service_time)
            list_TW.append(tw + waiting_time)
            list_TRES.append(env.now - arrival_time)

            global completed_jobs
            completed_jobs = completed_jobs + 1
            if nobag:
                global no_bag_passengers_completed
                no_bag_passengers_completed += 1
            if precheck:
                global pre_check_passengers_completed
                pre_check_passengers_completed += 1


def process_b3(env, name, passenger_scanner, arrival_time, waiting_time, service_time):
    print('Zone B3: %s Baggage arrives at the Baggage scanner at %.2f.' % (name, env.now))
    tw = env.now
    with passenger_scanner.machine.request() as request:
        yield request
        tw = env.now - tw
        ts = env.now
        print('Zone B3: %s starts Baggage scanning %.2f.' % (name, env.now))
        yield env.process(passenger_scanner.serve())
        ts = env.now - ts
        print('Zone B3: %s Finished Baggage scanning %.2f.\t || Process B3 SERVICE TIME: %d / WAITING TIME: %d' % (
            name, env.now, ts, tw))


def process_d(env, name, passenger_scanner, arrival_time, waiting_time, service_time, nobag, precheck):
    print('Zone D: %s arrives at the Additional scanner at %.2f.' % (name, env.now))
    tw = env.now
    with passenger_scanner.machine.request() as request:
        yield request
        tw = env.now - tw
        ts = env.now
        print('Zone D: %s starts Additional scanning %.2f.' % (name, env.now))
        yield env.process(passenger_scanner.serve())
        ts = env.now - ts
        print('Zone D: %s Finished Additional scanning %.2f.\t || Process D SERVICE TIME: %d / WAITING TIME: %d' % (
            name, env.now, ts, tw))
        print(
            f'{b_colors.OKBLUE}Zone D: %s Left the airport at %.2f\t || TOTAL_TW: %d / TOTAL TS: %d / RESPONSE TIME: %d{b_colors.ENDC}' % (
                name, env.now, (tw + waiting_time), (ts + service_time), (env.now - arrival_time)))
        list_TS.append(ts + service_time)
        list_TW.append(tw + waiting_time)
        list_TRES.append(env.now - arrival_time)
        global completed_jobs
        completed_jobs = completed_jobs + 1
        if nobag:
            global no_bag_passengers_completed
            no_bag_passengers_completed += 1
        if precheck:
            global pre_check_passengers_completed
            pre_check_passengers_completed += 1


def setup(env, allow_no_baggage, allow_pre_check):

    num_servers = 3
    number_of_passengers = 0

    a_time = 2
    b1_time = 10
    b2_time = 3
    b3_time = 3
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
        yield env.timeout(random.expovariate(0.1))  # Poisson arrivals
        number_of_passengers += 1
        env.process(process_a(env, 'Passenger %d' % number_of_passengers, id_check_booth))


def average(lst):
    return sum(lst) / len(lst)


# Setup and start the simulation
print('Airport Simulation \n')
random.seed(RANDOM_SEED)

env = simpy.Environment()
env.process(setup(env, allow_no_baggage, allow_pre_check))
env.run(until=OBS_TIME)
print(
    f'{b_colors.WARNING}\nPerformance metrics: Avg TW: %.2f, Avg TS: %.2f, Avg response time: %.2f\nCompleted %d jobs, %d with no bags and %d precheck' % (
        average(list_TW), average(list_TS), average(list_TRES), completed_jobs, no_bag_passengers, pre_check_passengers_completed))
print('Passengers with no baggage = %d' % no_bag_passengers)
print('Pre check program passengers %d' % pre_check_passengers)

plt.xlabel('Performance metrics')
plt.plot(list_TW, label='Waiting Time')
plt.plot(list_TS, label='Service Time')
plt.plot(list_TRES, label='Response Time')
plt.legend()
plt.show()
