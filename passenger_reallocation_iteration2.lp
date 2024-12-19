\ Model PassengerMixFlow
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  150 t_1^0 + 170 t_2^0 + 80 t_3^0 + 70 t_4^0 + 50 t_5^0 + 120 t_6^0
   + 100 t_7^0 + 100 t_8^0 + 140 t_9^0 + 80 t_10^0 + 150 t_11^0
   + 180 t_12^0 + 100 t_13^0 + 75 t_14^0 + 80 t_15^0 + 155 t_2^1 + 66 t_3^4
   + 165 t_12^11
Subject To
 Flight_101_Spill: t_6^0 + t_13^0 >= 42
 Flight_102_Spill: t_1^0 + t_7^0 - 0.1 t_2^1 >= 62
 Flight_104_Spill: t_2^0 + t_8^0 + t_2^1 >= 82
 Flight_201_Spill: t_5^0 + t_7^0 + t_11^0 - 0.1 t_12^11 >= 36
 Flight_202_Spill: t_3^0 + t_10^0 + t_13^0 + t_3^4 >= 117
 Flight_203_Spill: t_8^0 + t_12^0 + t_12^11 >= 142
 Flight_204_Spill: t_4^0 - 0.2 t_3^4 >= -8
 Flight_301_Spill: t_10^0 + t_14^0 >= 56
 Flight_302_Spill: t_5^0 + t_9^0 >= 82
 Flight_303_Spill: t_15^0 >= -64
 Demand_Limit_1: t_1^0 <= 90
 Demand_Limit_2: t_2^0 + t_2^1 <= 120
 Demand_Limit_3: t_3^0 + t_3^4 <= 70
 Demand_Limit_4: t_4^0 <= 100
 Demand_Limit_5: t_5^0 <= 50
 Demand_Limit_6: t_6^0 <= 120
 Demand_Limit_7: t_7^0 <= 80
 Demand_Limit_8: t_8^0 <= 70
 Demand_Limit_9: t_9^0 <= 140
 Demand_Limit_10: t_10^0 <= 125
 Demand_Limit_11: t_11^0 <= 50
 Demand_Limit_12: t_12^0 + t_12^11 <= 180
 Demand_Limit_13: t_13^0 <= 30
 Demand_Limit_14: t_14^0 <= 75
 Demand_Limit_15: t_15^0 <= 80
 NonNegative_t_1_0: t_1^0 >= 0
 NonNegative_t_2_0: t_2^0 >= 0
 NonNegative_t_3_0: t_3^0 >= 0
 NonNegative_t_4_0: t_4^0 >= 0
 NonNegative_t_5_0: t_5^0 >= 0
 NonNegative_t_6_0: t_6^0 >= 0
 NonNegative_t_7_0: t_7^0 >= 0
 NonNegative_t_8_0: t_8^0 >= 0
 NonNegative_t_9_0: t_9^0 >= 0
 NonNegative_t_10_0: t_10^0 >= 0
 NonNegative_t_11_0: t_11^0 >= 0
 NonNegative_t_12_0: t_12^0 >= 0
 NonNegative_t_13_0: t_13^0 >= 0
 NonNegative_t_14_0: t_14^0 >= 0
 NonNegative_t_15_0: t_15^0 >= 0
 NonNegative_t_2^1: t_2^1 >= 0
 NonNegative_t_3^4: t_3^4 >= 0
 NonNegative_t_12^11: t_12^11 >= 0
Bounds
End
