#ifndef TH_H_
#define TH_H_

int from_string_th(struct timeval *tv, char *string);
void component_th(struct timeval *result, unsigned int ms);
int cmp_th(struct timeval *alpha, struct timeval *beta);
int add_th(struct timeval *sigma, struct timeval *alpha, struct timeval *beta);
int sub_th(struct timeval *delta, struct timeval *alpha, struct timeval *beta);

#endif
