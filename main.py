"""
    Script to find the similarity between query and database. Also aims to do topic modelling and predict missing features in new, unseen documents
"""
import sys
sys.dont_write_bytecode = True

import nltk, string, sklearn, os, time, scipy, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from TextFile import *
from DerivedClass import *
from Assigner import *


def get_top_n_words(tf_matrix,n):
    """
        Get a list of the top n words with the highest frequency from each row in the tf matrix
    """
    words = []
    for row in tf_matrix:
        sortMat = {}
        for ind,val in enumerate(row):
            sortMat[ind] = val
        for i in sorted(sortMat.values())[-n:]:
            index = list(sortMat.keys())[list(sortMat.values()).index(i)]
            words.append(index)
            del sortMat[index]

    words = list(set(words))

    return words


def find_best_LDA(tf_matrix,num_topics):
    """
        Grid searching different parameters of LDA to find best model
    """
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.model_selection import GridSearchCV
    params = {'n_components':num_topics}
    lda = LatentDirichletAllocation(max_doc_update_iter=200,learning_method='batch',max_iter=200,evaluate_every=10,perp_tol=1e-4)
    t0 = time.time()
    model = GridSearchCV(lda,param_grid=params,cv=2)
    model.fit(tf_matrix)
    best_model = model.best_estimator_
    print('time taken = %d',time.time()-t0)
    #print(model.best_params_); print(model.best_score_)
    #np.save('grid_scores.npy',model.cv_results_)

    return best_model


def print_top_n_words_best_LDA(tf_vectorizer,best_lda,n_top_words=15):
    tf_words = tf_vectorizer.get_feature_names()
    for idx, topic in enumerate(best_lda.components_):
        message = "Topic %d: " % (idx)
        message += ", ".join([tf_words[i] for i in topic.argsort()[:-n_top_words - 1:-1]])
        print(message)

    return


def nth_dominant_topic_best_LDA(best_lda,best_lda_output,num,n=1):
    topics = ["Topic" + str(i) for i in range(best_lda.n_components)]
    docs = ["Doc" + str(i) for i in range(num)]
    df_doc_topic = pd.DataFrame(best_lda_output,columns=topics,index=docs)
    dominant_topic = np.argsort(df_doc_topic.values,axis=1)
    df_doc_topic['dominant_topic_num'] = dominant_topic[:,-n]

    m = scipy.stats.mode(dominant_topic)
    print(m)
    plt.bar(m[0].flatten(),m[1].flatten())
    plt.show()
    
    return df_doc_topic


def topic_distribution_best_LDA(df_doc_topic):
    topic_distr = df_doc_topic['dominant_topic_num'].value_counts().reset_index(name="Num Docs")
    topic_distr.columns = ['Topic Num','Num Docs']
    unique_topics = len(df_doc_topic['dominant_topic_num'].value_counts().index.tolist())

    return topic_distr, unique_topics


def cluster_docs(best_lda_output,clusters=0,method='kmeans'):
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=clusters)
    km.fit(best_lda_output)
    ypred = km.predict(best_lda_output)

    from sklearn.cluster import SpectralClustering
    sc = SpectralClustering(n_clusters=clusters).fit_predict(best_lda_output)
    
    from sklearn.decomposition import TruncatedSVD
    svd = TruncatedSVD(n_components=2)
    lda_svd = svd.fit_transform(best_lda_output)
    x = lda_svd[:,0]
    y = lda_svd[:,1]

    print(svd.explained_variance_ratio_)
    plt.figure
    if method == 'kmeans':
        plt.scatter(x,y, c=ypred, s=50, cmap='viridis')
    elif method == 'spectral':
        plt.scatter(x,y, c=sc, s=50, cmap='viridis')
    plt.xlabel('comp 1')
    plt.ylabel('comp 2')
    plt.title('topic clusters')
    plt.show()

    return


def main():
    start = time.time()

    ##### Testing MESH class
    mv = MESH('MESH Terms.txt','')
    #mv.create_MESH_vocab_and_IDmapping(); mv.save_MESH_IDmapping('MESH ID Mapping.txt')
    mesh_id_mapping = mv.read_MESH_IDmapping('MESH ID Mapping.txt')
    #print(mesh_id_mapping['adult'])
    
    ##### Testing Corpus class
    folder = "corpus/"
    num = 100
    corp = Corpus(folder,n=num)
    
    ##### Vectorizing
    #tf_vectorizer, tf_matrix = corp.vectorize_corpus(corp.clean(),voc)
    #tv = q.transform_query(tf_vectorizer).flatten()

    ##### Getting data
    tf = TextFile('Medical Case Reports.txt','',encode='latin-1')
    mesh_terms = tf.get_MESH_terms()
    ui = tf.get_UI(mesh_id_mapping)
    keywords = tf.get_keywords()
    titles = tf.get_titles()

    ##### Assigning ICD10 codes
    asg = Assigner('MESH_ICD10_Mapping.csv',mesh_id_mapping)
    #mesh_codes = asg.assign_MESHterms_ICD10(ui)
    #keywords_codes = asg.assign_keywords_ICD10(keywords)
    #titles_codes = asg.assign_titles_ICD10(titles)
    #asg.create_stopword_list()
    #asg.assign_MESHterms_partial_match_single_codes()
    tot = asg.assign_all_ICD10(ui,keywords,titles)
    #asg.write_codes_to_csv(tot,'test.csv')  # Case Reports_ICD10_Mapping.csv

    print(time.time()-start)
    """
    ## Do calculations on doc matrix
    prod = tf_matrix.dot(np.ones((tf_matrix.shape[1],1)))
    ind = np.argmax(tf_matrix,axis=1)
    last_n_words = 15
    words = get_top_n_words(tf_matrix,last_n_words); terms = [MESHvocab[i] for i in words]

    ## LDA
    num_topics = [20]
    best_lda = find_best_LDA(tf_matrix,num_topics)
    best_lda_output = best_lda.transform(tf_matrix)
    print_top_n_words_best_LDA(tf_vectorizer,best_lda,n_top_words=15)
    test_lda = best_lda.transform(test)
    print(test_lda)
    print(np.argmax(test_lda,axis=1))
    message_1 = [tf_vectorizer.get_feature_names()[i] for i in best_lda.components_[int(np.argmax(test_lda,axis=1))].argsort()[:-30-1:-1]]
    print("Most dominant topic: ",message_1); print('\n')
    second_best_arg = test_lda.argsort().flatten()[-2]
    message_2 = [tf_vectorizer.get_feature_names()[i] for i in best_lda.components_[second_best_arg].argsort()[:-30-1:-1]]
    print("2nd dominant topic: ",message_2); print('\n')
    third_best_arg = test_lda.argsort().flatten()[-3]
    message_3 = [tf_vectorizer.get_feature_names()[i] for i in best_lda.components_[third_best_arg].argsort()[:-30-1:-1]]
    print("3rd dominant topic: ",message_3); print('\n')
    fourth_best_arg = test_lda.argsort().flatten()[-4]
    message_4 = [tf_vectorizer.get_feature_names()[i] for i in best_lda.components_[fourth_best_arg].argsort()[:-30-1:-1]]
    print("4th dominant topic: ",message_4)

    ## Analysis of LDA
    dominant_topic = nth_dominant_topic_best_LDA(best_lda,best_lda_output,num,n=1)
    print(dominant_topic)
    topic_distr,unique_topics = topic_distribution_best_LDA(dominant_topic)
    print(topic_distr)
    #cluster_docs(best_lda_output,clusters=unique_topics,method='kmeans')
   """

main()