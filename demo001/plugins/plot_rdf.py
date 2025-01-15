import numpy as np
import matplotlib.pyplot as plt

nbins = 100 # define the number of bins in the RDF

with open("/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/rdf/RDF.rdf", "r") as f: # read the licl.rdf file
    lines = f.readlines()
    lines = lines[3:]
    data = np.zeros((nbins, 7))  
    count = 0  

    for line in lines:  
        nums = line.split()      
        if len(nums) == 8:  
            for i in range(1, 8):  
                data[int(nums[0])-1, i-1] += float(nums[i])  # accumulatie data for each bin  
        if len(nums) == 2:  
            count += 1         # count the number of accumulations for each bin
       
ave_rdf = data / count  # calculate the averaged RDF data
np.savetxt('/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/rdf/ave_rdf.txt', ave_rdf)

# with open("/work/wangs/DeepMD-kit/deepmd-kit/examples/water/lmp/testTanh10_h2o.rdf", "r") as f: # read the licl.rdf file
#     lines = f.readlines()
#     lines = lines[3:]
#     data2 = np.zeros((nbins, 7))  
#     count2 = 0  

#     for line in lines:  
#         nums = line.split()      
#         if len(nums) == 8:  
#             for i in range(1, 8):  
#                 data2[int(nums[0])-1, i-1] += float(nums[i])  # accumulatie data2 for each bin  
#         if len(nums) == 2:  
#             count2 += 1         # count2 the number of accumulations for each bin
       
# ave_rdf2 = data2 / count2  # calculate the averaged RDF data
# np.savetxt('ave_rdf2.txt', ave_rdf2)


# labels1 = ["DeepMD","DeepMD","DeepMD"]
# colors1 = ['Red','green','blue']

# # labels2 = ["Ours"]
# # colors2 = ["Blue"]

# for i, label, color in zip(range(1, 3, 2), labels1, colors1):
#     plt.plot(ave_rdf[:, 0], ave_rdf[:, i], label=label, color=color)

# # for i, label, color in zip(range(1, 7, 2), labels2, colors2):
# #     plt.plot(ave_rdf2[:, 0], ave_rdf2[:, i], label=label, color=color)

# plt.xlabel('r/A')
# plt.text(0.05, 0.95, '(a) g$_{O-O}$(r)', transform=plt.gca().transAxes,
#          fontsize=18, verticalalignment='top', horizontalalignment='left')
# plt.legend(fontsize=14)
# plt.savefig('/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/rdf/txt3.png',dpi = 300)
# plt.show()

plt.figure(1)
plt.plot(ave_rdf[:, 0], ave_rdf[:, 1], label='O-O', color='red')
plt.xlabel('r/Å')
plt.ylabel('g(r)')
plt.text(0.05, 0.95, 'g$_{O-O}$(r)', transform=plt.gca().transAxes,
         fontsize=18, verticalalignment='top', horizontalalignment='left')
plt.legend(fontsize=14)
plt.savefig('/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/rdf/fig1.png', dpi=300)
plt.close()

# 图 2: O-H RDF
plt.figure(2)
plt.plot(ave_rdf[:, 0], ave_rdf[:, 3], label='O-H', color='blue')
plt.xlabel('r/Å')
plt.ylabel('g(r)')
plt.text(0.05, 0.95, 'g$_{O-H}$(r)', transform=plt.gca().transAxes,
         fontsize=18, verticalalignment='top', horizontalalignment='left')
plt.legend(fontsize=14)
plt.savefig('/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/rdf/fig2.png', dpi=300)
plt.close()

# 图 3: H-H RDF
plt.figure(3)
plt.plot(ave_rdf[:, 0], ave_rdf[:, 5], label='H-H', color='green')
plt.xlabel('r/Å')
plt.ylabel('g(r)')
plt.text(0.05, 0.95, 'g$_{H-H}$(r)', transform=plt.gca().transAxes,
         fontsize=18, verticalalignment='top', horizontalalignment='left')
plt.legend(fontsize=14)
plt.savefig('/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/rdf/fig3.png', dpi=300)
plt.close()