/*----------------------------------------------------------------------*/
/*                           BIBLIOGRAPHY                               */
/*  Dole, Stephen H.  "Formation of Planetary Systems by Aggregation:   */
/*      a Computer Simulation"  October 1969,  Rand Corporation Paper   */
/*	P-4226.								*/
/*----------------------------------------------------------------------*/


/* A few variables global to the entire program:		*/
#include "structs.h"

/* Now for some variables global to the accretion process:      */
int dust_left;
double r_inner, r_outer, reduced_mass, dust_density, cloud_eccentricity;
dust_pointer dust_head;


void
set_initial_conditions (double inner_limit_of_dust, double outer_limit_of_dust)
{
    dust_head = (dust_bands *)malloc(sizeof(dust_bands));
    planet_head = NULL;
    dust_head->next_band = NULL;
    dust_head->outer_edge = outer_limit_of_dust;
    dust_head->inner_edge = inner_limit_of_dust;
    dust_head->dust_present = TRUE;
    dust_head->gas_present = TRUE;
    dust_left = TRUE;
    cloud_eccentricity = 0.2;
}

double
stellar_dust_limit (double stellar_mass_ratio)
{
    return(200.0 * pow(stellar_mass_ratio,(1.0 / 3.0)));
}

double
innermost_planet (double stellar_mass_ratio)
{
    return(0.3 * pow(stellar_mass_ratio,(1.0 / 3.0)));
}

double
outermost_planet (double stellar_mass_ratio)
{
    return(50.0 * pow(stellar_mass_ratio,(1.0 / 3.0)));
}

double
inner_effect_limit (double a, double e, double mass)
{
    return (a * (1.0 - e) * (1.0 - mass) / (1.0 + cloud_eccentricity));
}

double
outer_effect_limit (double a, double e, double mass)
{
    return (a * (1.0 + e) * (1.0 + reduced_mass) / (1.0 - cloud_eccentricity));
}

int
dust_available (double inside_range, double outside_range)
{
    dust_pointer current_dust_band;
    int dust_here;

    current_dust_band = dust_head;
    while ((current_dust_band != NULL)
           && (current_dust_band->outer_edge < inside_range))
        current_dust_band = current_dust_band->next_band;
    if (current_dust_band == NULL)
        dust_here = FALSE;
    else dust_here = current_dust_band->dust_present;
    while ((current_dust_band != NULL)
           && (current_dust_band->inner_edge < outside_range)) {
        dust_here = dust_here || current_dust_band->dust_present;
        current_dust_band = current_dust_band->next_band;
    }
    return(dust_here);
}

void
update_dust_lanes (double min, double max, double mass, double crit_mass, double body_inner_bound, double body_outer_bound)
{
    int gas;
    dust_pointer node1, node2, node3;

    dust_left = FALSE;
    if ((mass > crit_mass))
        gas = FALSE;
    else
        gas = TRUE;
    node1 = dust_head;
    while ((node1 != NULL)) {
        if (((node1->inner_edge < min) && (node1->outer_edge > max))) {
            node2 = (dust_bands *)malloc(sizeof(dust_bands));
            node2->inner_edge = min;
            node2->outer_edge = max;
            if ((node1->gas_present == TRUE))
                node2->gas_present = gas;
            else
                node2->gas_present = FALSE;
            node2->dust_present = FALSE;
            node3 = (dust_bands *)malloc(sizeof(dust_bands));
            node3->inner_edge = max;
            node3->outer_edge = node1->outer_edge;
            node3->gas_present = node1->gas_present;
            node3->dust_present = node1->dust_present;
            node3->next_band = node1->next_band;
            node1->next_band = node2;
            node2->next_band = node3;
            node1->outer_edge = min;
            node1 = node3->next_band;
        } else if (((node1->inner_edge < max) && (node1->outer_edge > max))) {
            node2 = (dust_bands *)malloc(sizeof(dust_bands));
            node2->next_band = node1->next_band;
            node2->dust_present = node1->dust_present;
            node2->gas_present = node1->gas_present;
            node2->outer_edge = node1->outer_edge;
            node2->inner_edge = max;
            node1->next_band = node2;
            node1->outer_edge = max;
            if ((node1->gas_present == TRUE))
                node1->gas_present = gas;
            else
                node1->gas_present = FALSE;
            node1->dust_present = FALSE;
            node1 = node2->next_band;
        } else if (((node1->inner_edge < min) && (node1->outer_edge > min))) {
            node2 = (dust_bands *)malloc(sizeof(dust_bands));
            node2->next_band = node1->next_band;
            node2->dust_present = FALSE;
            if ((node1->gas_present == TRUE))
                node2->gas_present = gas;
            else
                node2->gas_present = FALSE;
            node2->outer_edge = node1->outer_edge;
            node2->inner_edge = min;
            node1->next_band = node2;
            node1->outer_edge = min;
            node1 = node2->next_band;
        } else if (((node1->inner_edge >= min) && (node1->outer_edge <= max))) {
            if ((node1->gas_present == TRUE))
                node1->gas_present = gas;
            node1->dust_present = FALSE;
            node1 = node1->next_band;
        } else if (((node1->outer_edge < min) || (node1->inner_edge > max)))
            node1 = node1->next_band;
    }
    node1 = dust_head;
    while ((node1 != NULL)) {
        if (((node1->dust_present)
             && (((node1->outer_edge >= body_inner_bound)
                  && (node1->inner_edge <= body_outer_bound)))))
            dust_left = TRUE;
        node2 = node1->next_band;
        if ((node2 != NULL)) {
            if (((node1->dust_present == node2->dust_present)
                 && (node1->gas_present == node2->gas_present))) {
                node1->outer_edge = node2->outer_edge;
                node1->next_band = node2->next_band;
                free(node2);
            }
        }
        node1 = node1->next_band;
    }
}

double collect_dust(last_mass, a, e, crit_mass, dust_band)
double last_mass, a, e, crit_mass;
dust_pointer dust_band;
{
    double mass_density, temp1, temp2, temp, temp_density, bandwidth, width, volume;

    temp = last_mass / (1.0 + last_mass);
    reduced_mass = pow(temp,(1.0 / 4.0));
    r_inner = inner_effect_limit(a, e, reduced_mass);
    r_outer = outer_effect_limit(a, e, reduced_mass);
    if ((r_inner < 0.0))
        r_inner = 0.0;
    if ((dust_band == NULL))
        return(0.0);
    else {
        if ((dust_band->dust_present == FALSE))
            temp_density = 0.0;
        else
            temp_density = dust_density;
        if (((last_mass < crit_mass) || (dust_band->gas_present == FALSE)))
            mass_density = temp_density;
        else
            mass_density = K * temp_density / (1.0 + sqrt(crit_mass / last_mass)
                                               * (K - 1.0));
        if (((dust_band->outer_edge <= r_inner)
             || (dust_band->inner_edge >= r_outer)))
            return(collect_dust(last_mass,a,e,crit_mass, dust_band->next_band));
        else {
            bandwidth = (r_outer - r_inner);
            temp1 = r_outer - dust_band->outer_edge;
            if (temp1 < 0.0)
                temp1 = 0.0;
            width = bandwidth - temp1;
            temp2 = dust_band->inner_edge - r_inner;
            if (temp2 < 0.0)
                temp2 = 0.0;
            width = width - temp2;
            temp = 4.0 * PI * pow(a,2.0) * reduced_mass
                   * (1.0 - e * (temp1 - temp2) / bandwidth);
            volume = temp * width;
            return(volume * mass_density
                   + collect_dust(last_mass,a,e,crit_mass,
                                  dust_band->next_band));
        }
    }
}


/*--------------------------------------------------------------------------*/
/*   Orbital radius is in AU, eccentricity is unitless, and the stellar     */
/*  luminosity ratio is with respect to the sun.  The value returned is the */
/*  mass at which the planet begins to accrete gas as well as dust, and is  */
/*  in units of solar masses.                                               */
/*--------------------------------------------------------------------------*/

double
critical_limit (double orbital_radius, double eccentricity, double stellar_luminosity_ratio)
{
    double temp, perihelion_dist;

    perihelion_dist = (orbital_radius - orbital_radius * eccentricity);
    temp = perihelion_dist * sqrt(stellar_luminosity_ratio);
    return(B * pow(temp,-0.75));
}



void
accrete_dust (double *seed_mass, double a, double e, double crit_mass, double body_inner_bound, double body_outer_bound)
{
    double new_mass, temp_mass;

    new_mass = (*seed_mass);
    do {
        temp_mass = new_mass;
        new_mass = collect_dust(new_mass,a,e,crit_mass,
                                dust_head);
    } while (!(((new_mass - temp_mass) < (0.0001 * temp_mass))));
    (*seed_mass) = (*seed_mass) + new_mass;
    update_dust_lanes(r_inner,r_outer,(*seed_mass),crit_mass,body_inner_bound,body_outer_bound);
}



void
coalesce_planetesimals (double a, double e, double mass, double crit_mass, double stellar_luminosity_ratio, double body_inner_bound, double body_outer_bound)
{
    planet_pointer node1, node2, node3;
    int coalesced;
    double temp, dist1, dist2, a3;

    coalesced = FALSE;
    node1 = planet_head;
    node2 = NULL;
    node3 = NULL;
    while ((node1 != NULL)) {
        node2 = node1;
        temp = node1->a - a;
        if ((temp > 0.0)) {
            dist1 = (a * (1.0 + e) * (1.0 + reduced_mass)) - a;
            /* x aphelion   */
            reduced_mass = pow((node1->mass / (1.0 + node1->mass)),(1.0 / 4.0));
            dist2 = node1->a
                    - (node1->a * (1.0 - node1->e) * (1.0 - reduced_mass));
        } else {
            dist1 = a - (a * (1.0 - e) * (1.0 - reduced_mass));
            /* x perihelion */
            reduced_mass = pow(node1->mass / (1.0 + node1->mass),(1.0 / 4.0));
            dist2 = (node1->a * (1.0 + node1->e) * (1.0 + reduced_mass))
                    - node1->a;
        }
        if (((fabs(temp) <= fabs(dist1)) || (fabs(temp) <= fabs(dist2)))) {
            printf("Collision between two planetesimals!\n");
            a3 = (node1->mass + mass) / ((node1->mass / node1->a) + (mass / a));
            temp = node1->mass * sqrt(node1->a) * sqrt(1.0 - pow(node1->e,2.0));
            temp = temp + (mass * sqrt(a) * sqrt(sqrt(1.0 - pow(e,2.0))));
            temp = temp / ((node1->mass + mass) * sqrt(a3));
            temp = 1.0 - pow(temp,2.0);
            if (((temp < 0.0) || (temp >= 1.0)))
                temp = 0.0;
            e = sqrt(temp);
            temp = node1->mass + mass;
            accrete_dust(&(temp),a3,e,stellar_luminosity_ratio,
                         body_inner_bound,body_outer_bound);
            node1->a = a3;
            node1->e = e;
            node1->mass = temp;
            node1 = NULL;
            coalesced = TRUE;
        } else
            node1 = node1->next_planet;
    }
    if (!(coalesced)) {
        node3 = (planets *)malloc(sizeof(planets));
        node3->a = a;
        node3->e = e;
        if ((mass >= crit_mass))
            node3->gas_giant = TRUE;
        else
            node3->gas_giant = FALSE;
        node3->mass = mass;
        if ((planet_head == NULL)) {
            planet_head = node3;
            node3->next_planet = NULL;
        } else {
            node1 = planet_head;
            if ((a < node1->a)) {
                node3->next_planet = node1;
                planet_head = node3;
            } else if ((planet_head->next_planet == NULL)) {
                planet_head->next_planet = node3;
                node3->next_planet = NULL;
            } else {
                while (((node1 != NULL) && (node1->a < a))) {
                    node2 = node1;
                    node1 = node1->next_planet;
                }
                node3->next_planet = node1;
                node2->next_planet = node3;
            }
        }
    }
}


planet_pointer
distribute_planetary_masses (double stellar_mass_ratio, double stellar_luminosity_ratio, double inner_dust, double outer_dust)
{
    double a, e, mass, crit_mass,
           planetesimal_inner_bound, planetesimal_outer_bound;

    set_initial_conditions(inner_dust,outer_dust);
    planetesimal_inner_bound = innermost_planet(stellar_mass_ratio);
    planetesimal_outer_bound = outermost_planet(stellar_mass_ratio);
    while (dust_left) {
        a = random_number(planetesimal_inner_bound,planetesimal_outer_bound);
        e = random_eccentricity( );
        mass = PROTOPLANET_MASS;
#ifdef VERBOSE
        printf("Checking %f AU.\n",a);
#endif
        if (dust_available(inner_effect_limit(a, e, mass),
                           outer_effect_limit(a, e, mass))) {
            printf(".. Injecting protoplanet.\n");
            dust_density = DUST_DENSITY_COEFF * sqrt(stellar_mass_ratio)
                           * exp(-ALPHA * pow(a,(1.0 / N)));
            crit_mass = critical_limit(a,e,stellar_luminosity_ratio);
            accrete_dust(&(mass),a,e,crit_mass,
                         planetesimal_inner_bound,
                         planetesimal_outer_bound);
            if ((mass != 0.0) && (mass != PROTOPLANET_MASS))
                coalesce_planetesimals(a,e,mass,crit_mass,
                                       stellar_luminosity_ratio,
                                       planetesimal_inner_bound,planetesimal_outer_bound);
            else printf(".. failed due to large neighbor.\n");
        }
#ifdef VERBOSE
        else printf(".. failed.\n");
#endif
    }
    return(planet_head);
}
